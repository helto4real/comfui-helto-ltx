from .guide_models import guide_summary, parse_guides_json
from .ltx_native import apply_guides

MAX_RESOLUTION = 16384
DEFAULT_GUIDES_JSON = "{\"version\":1,\"guides\":[]}"


def stage_input_types(include_guides_json=False, include_image_guides=False):
    final_size_tip = "Target output size for this stage. With half_size_first_pass enabled and no latent connected, the internal latent uses half this value."
    required = {
        "positive": ("CONDITIONING", {"tooltip": "Positive conditioning to augment with native LTXV guide metadata."}),
        "negative": ("CONDITIONING", {"tooltip": "Negative conditioning to augment with matching native LTXV guide metadata."}),
        "vae": ("VAE", {"tooltip": "LTXV VAE used to encode selected guide images and optional start image sequences."}),
        "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": final_size_tip}),
        "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": final_size_tip}),
        "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 0.01, "tooltip": "Frames per second used only when timing_mode is seconds."}),
        "num_frames": ("INT", {"default": 97, "min": 1, "max": MAX_RESOLUTION, "step": 1, "tooltip": "Pixel frame count used for timing, negative frame positions, and internally-created empty latents."}),
        "timing_mode": (["frame", "seconds"], {"default": "frame", "tooltip": "Interpret manual guide positions as frame indexes or seconds."}),
        "resize_mode": (["contain", "pad", "stretch", "crop"], {"default": "contain", "tooltip": "How guide images are resized before VAE encoding. contain/pad preserves aspect ratio with padding."}),
        "duplicate_policy": (["error", "keep_first", "keep_last", "offset_next"], {"default": "error", "tooltip": "How to handle manual guide images that resolve to the same frame."}),
        "pad_color": ("STRING", {"default": "0,0,0", "tooltip": "RGB padding color for contain/pad resize mode. Accepts r,g,b or #rrggbb."}),
        "img_compression": ("INT", {"default": 35, "min": 0, "max": 100, "step": 1, "tooltip": "Native LTXV image compression applied before guide encoding. Set 0 to disable."}),
        "half_size_first_pass": ("BOOLEAN", {"default": False, "tooltip": "For 2x LTX upscale workflows: when no latent is connected, create and guide a half-size first-pass latent. Width/height should be the final target size."}),
        "global_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Multiplier applied to every manual guide strength and start sequence strength."}),
    }
    if include_guides_json:
        required["guides_json"] = ("STRING", {"default": DEFAULT_GUIDES_JSON, "tooltip": "Hidden serialized guide data used by the custom UI and saved in workflows."})
    if include_image_guides:
        required["image_guides"] = ("IMAGE_GUIDES", {"tooltip": "Reusable guide payload from LTX 2.3 Image Guide Manager."})
    return {
        "required": required,
        "optional": {
            "latent": ("LATENT", {"tooltip": "Optional existing video latent. When connected, its shape is used and half_size_first_pass does not resize it."}),
            "start_images": ("IMAGE", {"tooltip": "Optional IMAGE batch from a video source. Applied as a native multi-frame guide starting at frame 0."}),
            "start_images_strength": ("FLOAT", {"default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Strength for the optional start image sequence before global_strength is applied."}),
        },
    }


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
    )


class LTX23MultiImageLatentGuide:
    @classmethod
    def INPUT_TYPES(cls):
        return stage_input_types(include_guides_json=True)

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Manage multiple image guides for native LTXV keyframe/latent guide workflows."

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
        )


class LTX23ImageGuideManager:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timing_mode": (["frame", "seconds"], {"default": "frame", "tooltip": "Interpret guide positions as frame indexes or seconds."}),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 0.01, "tooltip": "Frames per second used to preview seconds-based guide positions."}),
                "num_frames": ("INT", {"default": 97, "min": 1, "max": MAX_RESOLUTION, "step": 1, "tooltip": "Frame count used to preview/clamp guide positions and negative frame indexes."}),
                "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Preview target width used for aspect-ratio warnings."}),
                "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32, "tooltip": "Preview target height used for aspect-ratio warnings."}),
                "guides_json": ("STRING", {"default": DEFAULT_GUIDES_JSON, "tooltip": "Hidden serialized guide data used by the custom UI and saved in workflows."}),
            }
        }

    RETURN_TYPES = ("IMAGE_GUIDES",)
    RETURN_NAMES = ("image_guides",)
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Select reusable LTX 2.3 image guides once and feed them into one or more apply nodes."

    @classmethod
    def IS_CHANGED(cls, guides_json, **kwargs):
        try:
            return guide_summary(parse_guides_json(guides_json))
        except Exception:
            return guides_json

    def run(self, timing_mode, fps, num_frames, width, height, guides_json):
        return (guides_json,)


class LTX23ApplyImageGuides:
    @classmethod
    def INPUT_TYPES(cls):
        return stage_input_types(include_image_guides=True)

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "run"
    CATEGORY = "LTX 2.3"
    DESCRIPTION = "Apply reusable LTX 2.3 image guides to the current sampler stage."

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
        fps,
        num_frames,
        timing_mode,
        resize_mode,
        duplicate_policy,
        pad_color,
        img_compression,
        half_size_first_pass,
        global_strength,
        image_guides,
        latent=None,
        start_images=None,
        start_images_strength=0.85,
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
            image_guides,
            latent,
            start_images,
            start_images_strength,
        )


NODE_CLASS_MAPPINGS = {
    "LTX23MultiImageLatentGuide": LTX23MultiImageLatentGuide,
    "LTX23ImageGuideManager": LTX23ImageGuideManager,
    "LTX23ApplyImageGuides": LTX23ApplyImageGuides,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LTX23MultiImageLatentGuide": "LTX 2.3 Multi Image Latent Guide",
    "LTX23ImageGuideManager": "LTX 2.3 Image Guide Manager",
    "LTX23ApplyImageGuides": "LTX 2.3 Apply Image Guides",
}


try:
    from . import routes  # noqa: F401
except Exception as exc:
    print(f"[LTX 2.3 Multi Image Latent Guide] Failed to register routes: {exc}")
