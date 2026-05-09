# LTX 2.3 Multi Image Latent Guide

ComfyUI custom node package for native LTXV image/keyframe guide workflows.

The node is named **LTX 2.3 Multi Image Latent Guide** and uses ComfyUI's native
`comfy_extras.nodes_lt.LTXVAddGuide` guide mechanism. It stores selected images
as folder aliases plus filenames in workflow JSON, applies aspect-ratio-aware
resizing, and outputs updated positive/negative conditioning plus an LTXV latent.

For native LTXV workflows, keep the existing downstream pattern: after sampling
with guide-appended latents, use `LTXVCropGuides` where your workflow expects it.
