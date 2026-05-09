import torch

import comfy.model_management
import comfy_extras.nodes_lt as nodes_lt

from .config_store import resolve_image_path
from .guide_models import parse_guides_json
from .image_io import load_guide_tensor


def resolve_timing(guides, timing_mode, fps, num_frames, duplicate_policy):
    resolved = []
    occupied = {}
    for index, guide in enumerate(guides):
        if not guide.enabled:
            continue
        frame = round(guide.position * fps) if timing_mode == "seconds" else int(round(guide.position))
        frame = max(0, min(int(num_frames) - 1, frame))
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
    latent = torch.zeros(
        [1, 128, ((int(num_frames) - 1) // 8) + 1, int(height) // 32, int(width) // 32],
        device=comfy.model_management.intermediate_device(),
    )
    return {"samples": latent}


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
    global_strength,
    guides_json,
    latent=None,
):
    guides = parse_guides_json(guides_json)
    resolved = resolve_timing(guides, timing_mode, float(fps), int(num_frames), duplicate_policy)

    if latent is None:
        latent = create_empty_latent(width, height, num_frames)
    else:
        latent = {
            **latent,
            "samples": latent["samples"].clone(),
            "noise_mask": latent.get("noise_mask", None).clone() if latent.get("noise_mask", None) is not None else None,
        }

    if not resolved:
        return positive, negative, latent

    scale_factors = vae.downscale_index_formula
    latent_image = latent["samples"]
    noise_mask = nodes_lt.get_noise_mask(latent)
    _, _, latent_length, latent_height, latent_width = latent_image.shape

    for frame_idx, guide in resolved:
        image_path = resolve_image_path(guide.folder_alias, guide.filename)
        image, _ = load_guide_tensor(image_path, width, height, resize_mode, pad_color)
        image = image.to(device=latent_image.device, dtype=torch.float32)
        _, encoded = nodes_lt.LTXVAddGuide.encode(vae, latent_width, latent_height, image, scale_factors)

        frame_idx, latent_idx = nodes_lt.LTXVAddGuide.get_latent_index(
            positive, latent_length, len(image), frame_idx, scale_factors
        )
        if latent_idx + encoded.shape[2] > latent_length:
            raise ValueError(f"Guide {guide.filename} exceeds latent length at frame {frame_idx}.")

        strength = max(0.0, min(1.0, float(global_strength) * float(guide.strength)))
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

    return positive, negative, {"samples": latent_image, "noise_mask": noise_mask}
