# AGENTS.md

## Project

This repository is a ComfyUI custom node package for native LTX Video workflows.
It is symlinked into:

```text
/home/thhel/git/ComfyUI/custom_nodes/comfyui-helto-ltx
```

The ComfyUI installation lives at:

```text
/home/thhel/git/ComfyUI
```

The node implemented here is:

```text
LTX 2.3 Multi Image Latent Guide
```

Its internal node class key is:

```text
LTX23MultiImageLatentGuide
```

## Direction

Prioritize native ComfyUI LTXV integration, not `ComfyUI_LTX2_SM`.

The current implementation uses ComfyUI's built-in native LTX guide mechanism from:

```text
/home/thhel/git/ComfyUI/comfy_extras/nodes_lt.py
```

Important native classes/functions:

```text
EmptyLTXVLatentVideo
LTXVAddGuide
LTXVCropGuides
get_noise_mask
```

`LTXVAddGuide` appends guide latents to the latent tensor and updates conditioning metadata:

```text
keyframe_idxs
guide_attention_entries
noise_mask
```

Downstream native LTX workflows often need `LTXVCropGuides` after sampling to remove appended guide frames.

## File Map

```text
__init__.py
  Exports node mappings and WEB_DIRECTORY.

nodes.py
  Defines the ComfyUI node class and input/output schema.

ltx_native.py
  Applies guides using native LTXV logic.
  This is the main LTX integration layer.

guide_models.py
  Guide/folder dataclasses and guides_json parsing.

config_store.py
  Folder config, guide-set paths, safe alias/path resolution.

image_io.py
  Image loading, RGB conversion, resize modes, tensor conversion, thumbnails.

routes.py
  ComfyUI aiohttp routes for folders, image listing, thumbnails, and guide sets.

web/ltx_multi_image_latent_guide.js
  Frontend extension and compact guide manager UI.

config/folders.json
  Folder alias config. Avoid storing absolute paths in workflow JSON.

config/guide_sets/
  Reusable guide-set JSON files.
```

## Data Model

Workflow JSON should store guide image references as folder alias plus filename, not absolute paths.

Guide item shape:

```json
{
  "folder_alias": "input",
  "filename": "example.png",
  "position": 0,
  "calculated_frame": 0,
  "strength": 1.0,
  "label": "",
  "enabled": true,
  "width": 1024,
  "height": 768
}
```

The frontend serializes guide data into the hidden `guides_json` widget.
The backend must treat frontend data as untrusted and repeat validation.

## Timing

Native LTXV guide placement ultimately uses pixel frame indices.

Current behavior:

```text
timing_mode = frame:
  frame = round(position)

timing_mode = seconds:
  frame = round(position * fps)
```

The node currently asks for `fps` and `num_frames`.
Future improvement: infer `num_frames` from a connected latent when available and only require `fps` for seconds mode.

Native LTXV latent frame count relation:

```text
latent_frames = ((pixel_frames - 1) // 8) + 1
pixel_frames = (latent_frames - 1) * 8 + 1
```

## Image Handling

Default resize behavior must preserve source aspect ratio and avoid cropping.

Modes:

```text
contain / pad:
  preserve aspect ratio, fit inside target, pad remaining area

stretch:
  force exact target size

crop:
  fill target size and center crop
```

Images are loaded from configured folders, converted to RGB, resized to target `width x height`, converted to ComfyUI IMAGE tensors, then passed to native LTXV guide encoding.

## Security

Keep path handling conservative.

Rules:

- Folder aliases are resolved server-side.
- Workflow JSON should avoid absolute paths.
- Reject unknown aliases.
- Reject unsupported extensions.
- Reject directory traversal.
- Resolve paths and ensure final image paths stay inside the configured folder root.
- Only list common image extensions:

```text
.png .jpg .jpeg .webp .bmp
```

## Frontend

Use ComfyUI frontend extension APIs from:

```javascript
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
```

Current UI is intentionally compact:

- Summary line in the node.
- Guide rows for enabled, filename, position, strength, move up/down, remove.
- Add folder/remove folder.
- Add guide image.
- Save/load guide sets.
- Hover preview panel with thumbnails and frame conversion.

Do not make the node huge by default. Prefer hover/temporary dialogs for detailed controls.

## Validation

Lightweight checks used so far:

```bash
python -B -m py_compile __init__.py guide_models.py config_store.py image_io.py ltx_native.py nodes.py routes.py
node --check web/ltx_multi_image_latent_guide.js
```

The local shell environment may not fully import ComfyUI because dependencies such as `safetensors` may not be installed in this shell. Full runtime validation should happen by restarting the actual ComfyUI instance and checking startup logs.

## Git Notes

The initial commit message is intentionally misspelled as requested:

```text
inital commit
```

Before committing, check:

```bash
git status --short
```

Do not commit generated `__pycache__` files or thumbnail cache output.
