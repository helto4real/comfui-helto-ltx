import re

import torch

import comfy.samplers
from comfy_extras.nodes_custom_sampler import CFGGuider, RandomNoise, SamplerCustomAdvanced
from comfy_extras.nodes_lt import (
    LTXVConcatAVLatent,
    LTXVConditioning,
    LTXVCropGuides,
    LTXVSeparateAVLatent,
    LTXVScheduler,
    ModelSamplingLTXV,
)
from comfy_extras.nodes_lt_audio import LTXVAudioVAEDecode, LTXVAudioVAEEncode, LTXVEmptyLatentAudio

from .guide_models import guide_summary, parse_guides_json
from .ltx_native import apply_guides

MAX_RESOLUTION = 16384
DEFAULT_GUIDES_JSON = "{\"version\":1,\"guides\":[]}"
DEFAULT_AUDIO_SAMPLE_RATE = 44100
GUIDE_DEFAULTS = {
    "fps": 24.0,
    "num_frames": 97,
    "timing_mode": "frame",
    "resize_mode": "contain",
    "duplicate_policy": "error",
    "pad_color": "0,0,0",
    "img_compression": 35,
    "global_strength": 1.0,
    "start_images_strength": 0.85,
    "lock_start_frames": False,
    "lock_end_frame": False,
}

GENERATION_DEFAULTS = {
    "seed": 0,
    "steps": 30,
    "cfg": 1.0,
    "sampler_name": "euler_cfg_pp",
    "max_shift": 2.05,
    "base_shift": 0.95,
    "stretch": True,
    "terminal": 0.1,
    "audio_mode": "passthrough",
    "sigma_mode": "ltx_scheduler",
    "manual_sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0",
}


def guide_settings_input_types(include_start_strength=True):
    settings = {
        "fps": ("FLOAT", {"default": GUIDE_DEFAULTS["fps"], "min": 1.0, "max": 240.0, "step": 0.01, "tooltip": "Frames per second used when timing_mode is seconds."}),
        "num_frames": ("INT", {"default": GUIDE_DEFAULTS["num_frames"], "min": 1, "max": MAX_RESOLUTION, "step": 8, "tooltip": "Pixel frame count used for timing, negative frame positions, and internally-created empty latents. Native LTXV lengths must be 8*n + 1, for example 97, 105, 113."}),
        "timing_mode": (["frame", "seconds"], {"default": GUIDE_DEFAULTS["timing_mode"], "tooltip": "Interpret manual guide positions as frame indexes or seconds."}),
        "resize_mode": (["contain", "pad", "stretch", "crop"], {"default": GUIDE_DEFAULTS["resize_mode"], "tooltip": "How guide images are resized before VAE encoding. contain/pad preserves aspect ratio with padding."}),
        "duplicate_policy": (["error", "keep_first", "keep_last", "offset_next"], {"default": GUIDE_DEFAULTS["duplicate_policy"], "tooltip": "How to handle manual guide images that resolve to the same frame."}),
        "pad_color": ("STRING", {"default": GUIDE_DEFAULTS["pad_color"], "tooltip": "RGB padding color for contain/pad resize mode. Accepts r,g,b or #rrggbb."}),
        "img_compression": ("INT", {"default": GUIDE_DEFAULTS["img_compression"], "min": 0, "max": 100, "step": 1, "tooltip": "Native LTXV image compression applied before guide encoding. Set 0 to disable."}),
        "global_strength": ("FLOAT", {"default": GUIDE_DEFAULTS["global_strength"], "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Multiplier applied to every manual guide strength and start sequence strength."}),
        "lock_start_frames": ("BOOLEAN", {"default": GUIDE_DEFAULTS["lock_start_frames"], "tooltip": "When enabled, frame 0 guides and start_images are written into the beginning video latent instead of only appended as guide references. VAE-level lock, not pixel-perfect copy."}),
        "lock_end_frame": ("BOOLEAN", {"default": GUIDE_DEFAULTS["lock_end_frame"], "tooltip": "When enabled, a manual guide resolving to the final frame is written into the final video latent instead of only appended as a guide reference. VAE-level lock, not pixel-perfect copy."}),
    }
    if include_start_strength:
        settings["start_images_strength"] = ("FLOAT", {"default": GUIDE_DEFAULTS["start_images_strength"], "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Strength for the optional start image sequence before global_strength is applied."})
    return settings


def stage_input_types(include_guides_json=False, include_image_guides=False, include_settings=True):
    final_size_tip = "Target output size for this stage. With half_size_first_pass enabled and no latent connected, the internal latent uses half this value."
    required = {
        "positive": ("CONDITIONING", {"tooltip": "Positive conditioning to augment with native LTXV guide metadata."}),
        "negative": ("CONDITIONING", {"tooltip": "Negative conditioning to augment with matching native LTXV guide metadata."}),
        "vae": ("VAE", {"tooltip": "LTXV VAE used to encode selected guide images and optional start image sequences."}),
        "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": final_size_tip}),
        "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": final_size_tip}),
        "half_size_first_pass": ("BOOLEAN", {"default": False, "tooltip": "For 2x LTX upscale workflows: when no latent is connected, create and guide a half-size first-pass latent. Width/height should be the final target size."}),
    }
    if include_settings:
        required.update(guide_settings_input_types(include_start_strength=True))
    if include_guides_json:
        required["guides_json"] = ("STRING", {"default": DEFAULT_GUIDES_JSON, "tooltip": "Hidden serialized guide data used by the custom UI and saved in workflows."})
    if include_image_guides:
        required["image_guides"] = ("IMAGE_GUIDES", {"tooltip": "Reusable guide payload from LTX 2.3 Image Guide Manager."})
    return {
        "required": required,
        "optional": {
            "latent": ("LATENT", {"tooltip": "Optional existing video latent. When connected, its shape is used and half_size_first_pass does not resize it."}),
            "start_images": ("IMAGE", {"tooltip": "Optional IMAGE batch from a video source. Applied as a native multi-frame guide starting at frame 0."}),
        },
    }


def generation_input_types():
    return {
        "required": {
            "model": ("MODEL", {"tooltip": "Native LTXV or LTXV AV model used for single-pass sampling."}),
            "clip": ("CLIP", {"tooltip": "Text encoder used to encode the positive and negative prompts."}),
            "vae": ("VAE", {"tooltip": "LTXV video VAE used for guide encoding and final video decode."}),
            "positive_prompt": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": True, "tooltip": "Positive text prompt encoded inside this generation node."}),
            "negative_prompt": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": True, "tooltip": "Negative text prompt encoded inside this generation node."}),
            "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Generated video width. Must be divisible by 32 after rounding down."}),
            "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Generated video height. Must be divisible by 32 after rounding down."}),
            **guide_settings_input_types(include_start_strength=True),
            "seed": ("INT", {"default": GENERATION_DEFAULTS["seed"], "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True, "tooltip": "Noise seed for generation."}),
            "steps": ("INT", {"default": GENERATION_DEFAULTS["steps"], "min": 1, "max": 10000, "tooltip": "Number of sampling steps for the native LTXV scheduler."}),
            "cfg": ("FLOAT", {"default": GENERATION_DEFAULTS["cfg"], "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01, "tooltip": "Classifier-free guidance scale."}),
            "sampler_name": (sampler_names(), {"default": default_sampler_name(), "tooltip": "Sampler algorithm used by ComfyUI's custom sampler."}),
            "max_shift": ("FLOAT", {"default": GENERATION_DEFAULTS["max_shift"], "min": 0.0, "max": 100.0, "step": 0.01, "tooltip": "Native LTXV model sampling and scheduler max shift."}),
            "base_shift": ("FLOAT", {"default": GENERATION_DEFAULTS["base_shift"], "min": 0.0, "max": 100.0, "step": 0.01, "tooltip": "Native LTXV model sampling and scheduler base shift."}),
            "stretch": ("BOOLEAN", {"default": GENERATION_DEFAULTS["stretch"], "tooltip": "Stretch scheduler sigmas to the terminal value."}),
            "terminal": ("FLOAT", {"default": GENERATION_DEFAULTS["terminal"], "min": 0.0, "max": 0.99, "step": 0.01, "tooltip": "Terminal scheduler sigma value when stretch is enabled."}),
            "sigma_mode": (["ltx_scheduler", "manual"], {"default": GENERATION_DEFAULTS["sigma_mode"], "tooltip": "Use native LTX scheduler sigmas or a pasted ManualSigmas-style schedule."}),
            "manual_sigmas": ("STRING", {"default": GENERATION_DEFAULTS["manual_sigmas"], "tooltip": "Comma/space separated sigma values used when sigma_mode is manual. Requires at least 2 values."}),
            "audio_mode": (["passthrough", "native_av"], {"default": GENERATION_DEFAULTS["audio_mode"], "tooltip": "passthrough outputs connected audio or silence. native_av samples audio/video latents with an LTXV AV model and audio_vae."}),
            "guides_json": ("STRING", {"default": DEFAULT_GUIDES_JSON, "tooltip": "Hidden serialized guide data used by the custom UI and saved in workflows."}),
        },
        "optional": {
            "start_images": ("IMAGE", {"tooltip": "Optional IMAGE batch from a video source. Applied as a native multi-frame guide starting at frame 0."}),
            "audio": ("AUDIO", {"tooltip": "Optional external audio. In passthrough mode it is trimmed/padded and output; in native_av mode it is encoded as a locked audio latent."}),
            "audio_vae": ("VAE", {"tooltip": "Required for native_av audio mode. Use the native LTXV Audio VAE Loader."}),
        },
    }


def guides_setting(guides_json, key):
    try:
        payload = parse_guides_json_payload(guides_json)
    except Exception:
        payload = {}
    return payload.get(key, GUIDE_DEFAULTS[key])


def parse_guides_json_payload(guides_json):
    import json

    if isinstance(guides_json, dict):
        return guides_json
    return json.loads(guides_json or DEFAULT_GUIDES_JSON)


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def sampler_names():
    return list(getattr(comfy.samplers, "SAMPLER_NAMES", ["euler"]))


def default_sampler_name():
    names = sampler_names()
    preferred = GENERATION_DEFAULTS["sampler_name"]
    return preferred if preferred in names else names[0]


def encode_prompt(clip, text):
    if clip is None:
        raise RuntimeError("CLIP input is required to encode prompts.")
    tokens = clip.tokenize(text or "")
    return clip.encode_from_tokens_scheduled(tokens)


def parse_manual_sigmas(manual_sigmas):
    values = re.findall(r"[-+]?(?:\d*\.*\d+)", manual_sigmas or "")
    sigmas = [float(value) for value in values]
    if len(sigmas) < 2:
        raise ValueError("manual_sigmas must contain at least 2 numeric sigma values.")
    return torch.FloatTensor(sigmas)


def node_output_value(output, index=0):
    return output[index]


def normalize_audio_duration(audio, num_frames, fps, sample_rate=None):
    fps = max(0.001, float(fps))
    sample_rate = int(sample_rate or (audio or {}).get("sample_rate", DEFAULT_AUDIO_SAMPLE_RATE))
    sample_count = max(1, int(round(float(num_frames) / fps * sample_rate)))
    if audio is None:
        return {
            "waveform": torch.zeros((1, 1, sample_count), dtype=torch.float32),
            "sample_rate": sample_rate,
        }

    waveform = audio["waveform"]
    if waveform.ndim == 1:
        waveform = waveform.reshape(1, 1, -1)
    elif waveform.ndim == 2:
        waveform = waveform.unsqueeze(0)
    waveform = waveform.clone()
    current = waveform.shape[-1]
    if current > sample_count:
        waveform = waveform[..., :sample_count]
    elif current < sample_count:
        pad = torch.zeros(
            (*waveform.shape[:-1], sample_count - current),
            dtype=waveform.dtype,
            device=waveform.device,
        )
        waveform = torch.cat((waveform, pad), dim=-1)
    return {"waveform": waveform, "sample_rate": sample_rate}


def match_audio_latent_to_target(audio_latent, target_latent):
    source = audio_latent["samples"]
    target = target_latent["samples"]
    matched = torch.zeros_like(target)
    batch = min(source.shape[0], target.shape[0])
    channels = min(source.shape[1], target.shape[1])
    frames = min(source.shape[2], target.shape[2])
    freq = min(source.shape[3], target.shape[3])
    matched[:batch, :channels, :frames, :freq] = source[:batch, :channels, :frames, :freq].to(
        device=target.device,
        dtype=target.dtype,
    )
    output = dict(target_latent)
    output["samples"] = matched
    output["noise_mask"] = torch.zeros_like(matched)
    return output


def is_ltxav_model(model):
    diffusion_model = getattr(getattr(model, "model", None), "diffusion_model", None)
    return diffusion_model is not None and diffusion_model.__class__.__name__ == "LTXAVModel"


def build_audio_for_generation(audio_mode, audio, audio_vae, num_frames, fps):
    output_audio = normalize_audio_duration(audio, num_frames, fps)
    if audio_mode == "passthrough":
        return None, output_audio

    if audio_mode != "native_av":
        raise ValueError(f"Unsupported audio_mode: {audio_mode}")
    if audio_vae is None:
        raise ValueError("audio_vae is required when audio_mode is native_av.")

    frame_rate = max(1, int(round(float(fps))))
    target_latent = node_output_value(LTXVEmptyLatentAudio.execute(int(num_frames), frame_rate, 1, audio_vae))
    if audio is None:
        return target_latent, output_audio

    encoded = node_output_value(LTXVAudioVAEEncode.execute(output_audio, audio_vae))
    return match_audio_latent_to_target(encoded, target_latent), output_audio


def decode_video_latent(vae, latent):
    samples = latent["samples"]
    if getattr(samples, "is_nested", False):
        samples = samples.unbind()[0]
    images = vae.decode(samples)
    if len(images.shape) == 5:
        images = images.reshape(-1, images.shape[-3], images.shape[-2], images.shape[-1])
    return images


def sample_ltx_video(
    model,
    positive,
    negative,
    video_latent,
    fps,
    seed,
    steps,
    cfg,
    sampler_name,
    max_shift,
    base_shift,
    stretch,
    terminal,
    sigma_mode,
    manual_sigmas,
    audio_latent=None,
):
    model = node_output_value(ModelSamplingLTXV.execute(model, max_shift, base_shift, video_latent))
    if sigma_mode == "manual":
        sigmas = parse_manual_sigmas(manual_sigmas)
    elif sigma_mode == "ltx_scheduler":
        sigmas = node_output_value(LTXVScheduler.execute(steps, max_shift, base_shift, stretch, terminal, video_latent))
    else:
        raise ValueError(f"Unsupported sigma_mode: {sigma_mode}")
    conditioning_output = LTXVConditioning.execute(positive, negative, fps)
    positive = node_output_value(conditioning_output, 0)
    negative = node_output_value(conditioning_output, 1)
    noise = node_output_value(RandomNoise.execute(seed))
    guider = node_output_value(CFGGuider.execute(model, positive, negative, cfg))
    sampler = comfy.samplers.sampler_object(sampler_name)

    sampling_latent = video_latent
    if audio_latent is not None:
        sampling_latent = node_output_value(LTXVConcatAVLatent.execute(video_latent, audio_latent))

    sampled = node_output_value(SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, sampling_latent), 1)
    if audio_latent is not None:
        separated = LTXVSeparateAVLatent.execute(sampled)
        video_latent = node_output_value(separated, 0)
        sampled_audio_latent = node_output_value(separated, 1)
    else:
        video_latent, sampled_audio_latent = sampled, None

    cropped = LTXVCropGuides.execute(positive, negative, video_latent)
    video_latent = node_output_value(cropped, 2)
    return video_latent, sampled_audio_latent


def build_guides_payload(guides_json, **settings):
    import json

    try:
        payload = parse_guides_json_payload(guides_json)
    except Exception:
        payload = {"version": 1, "guides": []}
    payload = dict(payload)
    payload["version"] = payload.get("version", 1)
    payload["guides"] = payload.get("guides", [])
    for key, value in settings.items():
        payload[key] = value
    return json.dumps(payload)


def run_apply_guides(
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
    if resize_mode == "pad":
        resize_mode = "contain"
    width = (int(width) // 32) * 32
    height = (int(height) // 32) * 32
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be at least 32.")
    return apply_guides(
        positive=positive,
        negative=negative,
        vae=vae,
        width=width,
        height=height,
        fps=fps,
        num_frames=num_frames,
        timing_mode=timing_mode,
        resize_mode=resize_mode,
        duplicate_policy=duplicate_policy,
        pad_color=pad_color,
        img_compression=img_compression,
        half_size_first_pass=half_size_first_pass,
        global_strength=global_strength,
        guides_json=guides_json,
        latent=latent,
        start_images=start_images,
        start_images_strength=start_images_strength,
        lock_start_frames=coerce_bool(lock_start_frames),
        lock_end_frame=coerce_bool(lock_end_frame),
    )


class LTX23MultiImageLatentGuide:
    @classmethod
    def INPUT_TYPES(cls):
        return stage_input_types(include_guides_json=True)

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "All-in-one native LTXV guide node: select images, apply guide metadata, and output guided conditioning plus latent."

    @classmethod
    def IS_CHANGED(cls, guides_json, **kwargs):
        try:
            guides = parse_guides_json(guides_json)
            return guide_summary(guides)
        except Exception:
            return guides_json

    def run(
        self,
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
        return run_apply_guides(
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
            latent,
            start_images,
            start_images_strength,
            lock_start_frames,
            lock_end_frame,
        )


class LTX23ImageGuideManager:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                **guide_settings_input_types(include_start_strength=True),
                "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Preview target width used for aspect-ratio warnings."}),
                "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Preview target height used for aspect-ratio warnings."}),
                "guides_json": ("STRING", {"default": DEFAULT_GUIDES_JSON, "tooltip": "Hidden serialized guide data used by the custom UI and saved in workflows."}),
            }
        }

    RETURN_TYPES = ("IMAGE_GUIDES",)
    RETURN_NAMES = ("image_guides",)
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Build a reusable LTX 2.3 image guide set and shared timing/strength settings for one or more apply nodes."

    @classmethod
    def IS_CHANGED(cls, guides_json, **kwargs):
        try:
            return guide_summary(parse_guides_json(guides_json))
        except Exception:
            return guides_json

    def run(
        self,
        fps,
        num_frames,
        timing_mode,
        resize_mode,
        duplicate_policy,
        pad_color,
        img_compression,
        global_strength,
        lock_start_frames,
        lock_end_frame,
        start_images_strength,
        width,
        height,
        guides_json,
    ):
        return (
            build_guides_payload(
                guides_json,
                fps=float(fps),
                num_frames=int(num_frames),
                timing_mode=timing_mode,
                resize_mode=resize_mode,
                duplicate_policy=duplicate_policy,
                pad_color=pad_color,
                img_compression=int(img_compression),
                global_strength=float(global_strength),
                lock_start_frames=coerce_bool(lock_start_frames),
                lock_end_frame=coerce_bool(lock_end_frame),
                start_images_strength=float(start_images_strength),
                width=int(width),
                height=int(height),
            ),
        )


class LTX23ApplyImageGuides:
    @classmethod
    def INPUT_TYPES(cls):
        return stage_input_types(include_image_guides=True, include_settings=False)

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Apply an IMAGE_GUIDES payload to one sampler stage, using this stage's width, height, latent, and half-size setting."

    @classmethod
    def IS_CHANGED(cls, image_guides, **kwargs):
        try:
            return guide_summary(parse_guides_json(image_guides))
        except Exception:
            return image_guides

    def run(
        self,
        positive,
        negative,
        vae,
        width,
        height,
        half_size_first_pass,
        image_guides,
        latent=None,
        start_images=None,
        **_legacy_inputs,
    ):
        return run_apply_guides(
            positive,
            negative,
            vae,
            width,
            height,
            guides_setting(image_guides, "fps"),
            guides_setting(image_guides, "num_frames"),
            guides_setting(image_guides, "timing_mode"),
            guides_setting(image_guides, "resize_mode"),
            guides_setting(image_guides, "duplicate_policy"),
            guides_setting(image_guides, "pad_color"),
            guides_setting(image_guides, "img_compression"),
            half_size_first_pass,
            guides_setting(image_guides, "global_strength"),
            image_guides,
            latent,
            start_images,
            guides_setting(image_guides, "start_images_strength"),
            guides_setting(image_guides, "lock_start_frames"),
            guides_setting(image_guides, "lock_end_frame"),
        )


class LTX23GenerateAllInOne:
    @classmethod
    def INPUT_TYPES(cls):
        return generation_input_types()

    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("images", "audio")
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Single-pass native LTXV generation with prompts, image guides, sampling, video decode, and optional audio output."

    @classmethod
    def IS_CHANGED(cls, guides_json=DEFAULT_GUIDES_JSON, **kwargs):
        try:
            guides_part = guide_summary(parse_guides_json(guides_json))
        except Exception:
            guides_part = guides_json
        tracked = [
            "positive_prompt",
            "negative_prompt",
            "width",
            "height",
            "fps",
            "num_frames",
            "timing_mode",
            "resize_mode",
            "duplicate_policy",
            "pad_color",
            "img_compression",
            "global_strength",
            "lock_start_frames",
            "lock_end_frame",
            "start_images_strength",
            "seed",
            "steps",
            "cfg",
            "sampler_name",
            "max_shift",
            "base_shift",
            "stretch",
            "terminal",
            "sigma_mode",
            "manual_sigmas",
            "audio_mode",
        ]
        return (guides_part, tuple((name, kwargs.get(name)) for name in tracked))

    def run(
        self,
        model,
        clip,
        vae,
        positive_prompt,
        negative_prompt,
        width,
        height,
        fps,
        num_frames,
        timing_mode,
        resize_mode,
        duplicate_policy,
        pad_color,
        img_compression,
        global_strength,
        lock_start_frames,
        lock_end_frame,
        start_images_strength,
        seed,
        steps,
        cfg,
        sampler_name,
        max_shift,
        base_shift,
        stretch,
        terminal,
        sigma_mode,
        manual_sigmas,
        audio_mode,
        guides_json,
        start_images=None,
        audio=None,
        audio_vae=None,
    ):
        width = (int(width) // 32) * 32
        height = (int(height) // 32) * 32
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be at least 32.")
        if sampler_name not in sampler_names():
            raise ValueError(f"Unknown sampler_name: {sampler_name}")
        if audio_mode == "native_av" and not is_ltxav_model(model):
            raise ValueError("audio_mode native_av requires an LTXV AV model.")

        positive = encode_prompt(clip, positive_prompt)
        negative = encode_prompt(clip, negative_prompt)
        positive, negative, video_latent = run_apply_guides(
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
            False,
            global_strength,
            guides_json,
            None,
            start_images,
            start_images_strength,
            lock_start_frames,
            lock_end_frame,
        )

        audio_latent, output_audio = build_audio_for_generation(audio_mode, audio, audio_vae, num_frames, fps)
        video_latent, sampled_audio_latent = sample_ltx_video(
            model=model,
            positive=positive,
            negative=negative,
            video_latent=video_latent,
            fps=fps,
            seed=int(seed),
            steps=int(steps),
            cfg=float(cfg),
            sampler_name=sampler_name,
            max_shift=float(max_shift),
            base_shift=float(base_shift),
            stretch=coerce_bool(stretch),
            terminal=float(terminal),
            sigma_mode=sigma_mode,
            manual_sigmas=manual_sigmas,
            audio_latent=audio_latent,
        )

        images = decode_video_latent(vae, video_latent)
        if audio_mode == "native_av" and audio is None and sampled_audio_latent is not None:
            output_audio = node_output_value(LTXVAudioVAEDecode.execute(sampled_audio_latent, audio_vae))
        return images, output_audio


NODE_CLASS_MAPPINGS = {
    "LTX23MultiImageLatentGuide": LTX23MultiImageLatentGuide,
    "LTX23ImageGuideManager": LTX23ImageGuideManager,
    "LTX23ApplyImageGuides": LTX23ApplyImageGuides,
    "LTX23GenerateAllInOne": LTX23GenerateAllInOne,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LTX23MultiImageLatentGuide": "LTX 2.3 Image Guides (All-in-One)",
    "LTX23ImageGuideManager": "LTX 2.3 Image Guide Manager",
    "LTX23ApplyImageGuides": "LTX 2.3 Apply Image Guides",
    "LTX23GenerateAllInOne": "LTX 2.3 Generate All-in-One",
}


try:
    from . import routes  # noqa: F401
except Exception as exc:
    print(f"[LTX 2.3 Multi Image Latent Guide] Failed to register routes: {exc}")
