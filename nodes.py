from .guide_models import guide_summary, parse_guides_json
from .ltx_native import apply_guides

MAX_RESOLUTION = 16384


class LTX23MultiImageLatentGuide:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE",),
                "width": ("INT", {"default": 768, "min": 64, "max": MAX_RESOLUTION, "step": 32}),
                "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 32}),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 0.01}),
                "num_frames": ("INT", {"default": 97, "min": 1, "max": MAX_RESOLUTION, "step": 1}),
                "timing_mode": (["frame", "seconds"], {"default": "frame"}),
                "resize_mode": (["contain", "pad", "stretch", "crop"], {"default": "contain"}),
                "duplicate_policy": (["error", "keep_first", "keep_last", "offset_next"], {"default": "error"}),
                "pad_color": ("STRING", {"default": "0,0,0"}),
                "global_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "guides_json": ("STRING", {"default": "{\"version\":1,\"guides\":[]}"}),
            },
            "optional": {
                "latent": ("LATENT",),
            },
        }

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
        global_strength,
        guides_json,
        latent=None,
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
            global_strength=global_strength,
            guides_json=guides_json,
            latent=latent,
        )


NODE_CLASS_MAPPINGS = {
    "LTX23MultiImageLatentGuide": LTX23MultiImageLatentGuide,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LTX23MultiImageLatentGuide": "LTX 2.3 Multi Image Latent Guide",
}


try:
    from . import routes  # noqa: F401
except Exception as exc:
    print(f"[LTX 2.3 Multi Image Latent Guide] Failed to register routes: {exc}")
