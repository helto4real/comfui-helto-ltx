import torch

import comfy.model_management
import comfy_extras.nodes_lt as nodes_lt

from .config_store import resolve_image_path
from .guide_models import parse_guides_json
from .image_io import load_guide_tensor, resize_tensor_images


def resolve_timing(guides, timing_mode, fps, num_frames, duplicate_policy):
    resolved = []
    occupied = {}
    num_frames = max(1, int(num_frames))
    for index, guide in enumerate(guides):
        if not guide.enabled:
            continue
        frame = round(guide.position * fps) if timing_mode == "seconds" else int(round(guide.position))
        if frame < 0:
            frame = num_frames + frame
        frame = max(0, min(num_frames - 1, frame))
        if frame in occupied:
            if duplicate_policy == "error":
                raise ValueError(f"Duplicate guide frame {frame}: {guide.filename}")
            if duplicate_policy == "keep_first":
                continue
            if duplicate_policy == "keep_last":
                prior = occupied[frame]
                resolved[prior] = None
                occupied[frame] = len(resolved)
            if duplicate_policy == "offset_next":
                while frame in occupied and frame < int(num_frames) - 1:
                    frame += 1
                if frame in occupied:
                    raise ValueError(f"Could not offset duplicate guide near final frame for {guide.filename}")
                occupied[frame] = len(resolved)
        else:
            occupied[frame] = len(resolved)
        resolved.append((frame, guide))
    return sorted([item for item in resolved if item is not None], key=lambda item: item[0])


def create_empty_latent(width, height, num_frames):
    num_frames = int(num_frames)
    if (num_frames - 1) % 8 != 0:
        lower = ((num_frames - 1) // 8) * 8 + 1
        upper = lower + 8
        raise ValueError(
            f"Native LTXV frame count must be 8*n + 1. "
            f"{num_frames} would create {lower} frames; use {lower} or {upper}."
        )
    latent = torch.zeros(
        [1, 128, ((num_frames - 1) // 8) + 1, int(height) // 32, int(width) // 32],
        device=comfy.model_management.intermediate_device(),
    )
    return {"samples": latent}


def half_size_dimension(value):
    return max(32, (int(value) // 2 // 32) * 32)


def preprocess_guide_image(image, img_compression):
    img_compression = int(img_compression)
    if img_compression <= 0:
        return image
    return torch.stack([nodes_lt.preprocess(frame, img_compression) for frame in image])


def native_cropped_frame_count(image_count, scale_factors):
    time_scale_factor = int(scale_factors[0])
    return ((int(image_count) - 1) // time_scale_factor) * time_scale_factor + 1


def append_native_guide(
    positive,
    negative,
    latent_image,
    noise_mask,
    vae,
    images,
    frame_idx,
    strength,
    scale_factors,
    label,
):
    _, _, latent_length, latent_height, latent_width = latent_image.shape
    _, encoded = nodes_lt.LTXVAddGuide.encode(vae, latent_width, latent_height, images, scale_factors)
    frame_idx, latent_idx = nodes_lt.LTXVAddGuide.get_latent_index(
        positive, latent_length, len(images), frame_idx, scale_factors
    )
    if latent_idx + encoded.shape[2] > latent_length:
        raise ValueError(f"Guide {label} exceeds latent length at frame {frame_idx}.")

    positive, negative, latent_image, noise_mask = nodes_lt.LTXVAddGuide.append_keyframe(
        positive=positive,
        negative=negative,
        frame_idx=frame_idx,
        latent_image=latent_image,
        noise_mask=noise_mask,
        guiding_latent=encoded,
        strength=strength,
        scale_factors=scale_factors,
    )

    if hasattr(nodes_lt, "_append_guide_attention_entry"):
        pre_filter_count = encoded.shape[2] * encoded.shape[3] * encoded.shape[4]
        positive, negative = nodes_lt._append_guide_attention_entry(
            positive,
            negative,
            pre_filter_count,
            list(encoded.shape[2:]),
            strength=strength,
        )
    return positive, negative, latent_image, noise_mask


def replace_latent_frames(latent_image, noise_mask, vae, images, latent_idx, strength, scale_factors, label):
    _, _, _, latent_height, latent_width = latent_image.shape
    _, encoded = nodes_lt.LTXVAddGuide.encode(vae, latent_width, latent_height, images, scale_factors)
    latent_idx = max(0, min(int(latent_idx), latent_image.shape[2] - 1))
    end_idx = min(latent_idx + encoded.shape[2], latent_image.shape[2])
    replace_len = end_idx - latent_idx
    if replace_len <= 0:
        raise ValueError(f"Locked guide {label} does not fit inside the latent.")

    channel_count = min(latent_image.shape[1], encoded.shape[1])
    latent_image = latent_image.clone()
    noise_mask = noise_mask.clone()
    latent_image[:, :channel_count, latent_idx:end_idx] = encoded[:, :channel_count, :replace_len]
    mask = torch.full(
        (noise_mask.shape[0], 1, replace_len, noise_mask.shape[3], noise_mask.shape[4]),
        1.0 - strength,
        dtype=noise_mask.dtype,
        device=noise_mask.device,
    )
    noise_mask[:, :, latent_idx:end_idx] = mask
    return latent_image, noise_mask


def apply_guides(
    positive,
    negative,
    vae,
    width,
    height,
    fps,
    num_frames,
    timing_mode,
    resize_mode,
    duplicate_policy,
    pad_color,
    img_compression,
    half_size_first_pass,
    global_strength,
    guides_json,
    latent=None,
    start_images=None,
    start_images_strength=0.85,
    lock_start_frames=False,
    lock_end_frame=False,
):
    guides = parse_guides_json(guides_json)

    if latent is None:
        if half_size_first_pass:
            width = half_size_dimension(width)
            height = half_size_dimension(height)
        latent = create_empty_latent(width, height, num_frames)
    else:
        latent = {
            **latent,
            "samples": latent["samples"].clone(),
            "noise_mask": latent.get("noise_mask", None).clone() if latent.get("noise_mask", None) is not None else None,
        }

    scale_factors = vae.downscale_index_formula
    latent_image = latent["samples"]
    noise_mask = nodes_lt.get_noise_mask(latent)
    _, _, latent_length, latent_height, latent_width = latent_image.shape
    effective_num_frames = (latent_length - 1) * scale_factors[0] + 1
    final_frame_idx = effective_num_frames - 1
    resolved = resolve_timing(guides, timing_mode, float(fps), effective_num_frames, duplicate_policy)
    start_sequence_applied = False

    if start_images is not None:
        if start_images.shape[0] <= 0:
            raise ValueError("Start image sequence is empty.")
        sequence_frame_count = native_cropped_frame_count(start_images.shape[0], scale_factors)
        for frame_idx, guide in resolved:
            if frame_idx < sequence_frame_count:
                raise ValueError(
                    f"Manual guide {guide.filename} at frame {frame_idx} overlaps the start image sequence."
                )

        sequence = resize_tensor_images(start_images, width, height, resize_mode, pad_color)
        sequence = sequence.to(device=latent_image.device, dtype=torch.float32)
        sequence_strength = max(0.0, min(1.0, float(global_strength) * float(start_images_strength)))
        if lock_start_frames:
            latent_image, noise_mask = replace_latent_frames(
                latent_image=latent_image,
                noise_mask=noise_mask,
                vae=vae,
                images=sequence,
                latent_idx=0,
                strength=sequence_strength,
                scale_factors=scale_factors,
                label="start image sequence",
            )
        else:
            sequence = preprocess_guide_image(sequence, img_compression)
            positive, negative, latent_image, noise_mask = append_native_guide(
                positive=positive,
                negative=negative,
                latent_image=latent_image,
                noise_mask=noise_mask,
                vae=vae,
                images=sequence,
                frame_idx=0,
                strength=sequence_strength,
                scale_factors=scale_factors,
                label="start image sequence",
            )
        start_sequence_applied = True

    if not resolved:
        if not start_sequence_applied:
            return positive, negative, latent
        return positive, negative, {"samples": latent_image, "noise_mask": noise_mask}

    for frame_idx, guide in resolved:
        image_path = resolve_image_path(guide.folder_alias, guide.filename)
        image, _ = load_guide_tensor(image_path, width, height, resize_mode, pad_color)
        image = image.to(device=latent_image.device, dtype=torch.float32)
        strength = max(0.0, min(1.0, float(global_strength) * float(guide.strength)))
        if lock_start_frames and frame_idx == 0:
            latent_image, noise_mask = replace_latent_frames(
                latent_image=latent_image,
                noise_mask=noise_mask,
                vae=vae,
                images=image,
                latent_idx=0,
                strength=strength,
                scale_factors=scale_factors,
                label=guide.filename,
            )
            continue
        if lock_end_frame and frame_idx == final_frame_idx:
            latent_image, noise_mask = replace_latent_frames(
                latent_image=latent_image,
                noise_mask=noise_mask,
                vae=vae,
                images=image,
                latent_idx=latent_length - 1,
                strength=strength,
                scale_factors=scale_factors,
                label=guide.filename,
            )
            continue

        image = preprocess_guide_image(image, img_compression)
        positive, negative, latent_image, noise_mask = append_native_guide(
            positive=positive,
            negative=negative,
            latent_image=latent_image,
            noise_mask=noise_mask,
            vae=vae,
            images=image,
            frame_idx=frame_idx,
            strength=strength,
            scale_factors=scale_factors,
            label=guide.filename,
        )

    return positive, negative, {"samples": latent_image, "noise_mask": noise_mask}
