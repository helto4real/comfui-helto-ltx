from .guide_models import guide_summary, parse_guides_json
from .ltx_native import apply_guides

MAX_RESOLUTION = 16384
DEFAULT_GUIDES_JSON = "{\"version\":1,\"guides\":[]}"
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


NODE_CLASS_MAPPINGS = {
    "LTX23MultiImageLatentGuide": LTX23MultiImageLatentGuide,
    "LTX23ImageGuideManager": LTX23ImageGuideManager,
    "LTX23ApplyImageGuides": LTX23ApplyImageGuides,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LTX23MultiImageLatentGuide": "LTX 2.3 Image Guides (All-in-One)",
    "LTX23ImageGuideManager": "LTX 2.3 Image Guide Manager",
    "LTX23ApplyImageGuides": "LTX 2.3 Apply Image Guides",
}


try:
    from . import routes  # noqa: F401
except Exception as exc:
    print(f"[LTX 2.3 Multi Image Latent Guide] Failed to register routes: {exc}")
