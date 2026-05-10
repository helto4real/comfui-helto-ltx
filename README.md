# ComfyUI Helto LTX

ComfyUI custom nodes for native LTX Video image guide workflows.

This package focuses on ComfyUI's built-in native LTXV guide path from
`comfy_extras.nodes_lt`, especially `LTXVAddGuide` and `LTXVCropGuides`.
It is intended for LTX 2.3 workflows that need multiple still-image guides,
start-frame image sequences, reusable guide sets, and two-stage low/high
resolution generation.

## Nodes

The package currently exposes three nodes in the `LTX 2.3` category:

```text
LTX 2.3 Image Guides (All-in-One)
LTX 2.3 Image Guide Manager
LTX 2.3 Apply Image Guides
```

The all-in-one node is the compatibility and convenience node. The Manager and
Apply nodes are the recommended setup for two-stage workflows, because one guide
list can feed both the low-resolution and high-resolution stages.

## Native LTXV Behavior

The nodes use native ComfyUI LTXV guide behavior instead of reimplementing a
separate LTX guide format.

Internally, guide images are encoded through native LTXV logic and appended to
the latent tensor. The positive and negative conditioning are updated with native
guide metadata:

```text
keyframe_idxs
guide_attention_entries
noise_mask
```

Because guide latents are appended to the latent tensor, native LTX workflows
usually need `LTXVCropGuides` after sampling to remove the guide frames from the
final latent before decode or before later workflow steps that expect the normal
video length.

## Recommended Workflows

### Simple Single-Stage Workflow

Use:

```text
LTX 2.3 Image Guides (All-in-One)
```

Connect:

```text
positive -> positive
negative -> negative
vae -> vae
latent -> latent, optional
start_images -> start_images, optional
```

Then feed the node outputs into the native LTX sampler path:

```text
positive -> guider/sampler positive
negative -> guider/sampler negative
latent -> sampler latent_image
```

After sampling, use native `LTXVCropGuides` if your downstream workflow expects
guide frames to be removed.

### Two-Stage Low/High Resolution Workflow

Use one manager and two apply nodes:

```text
LTX 2.3 Image Guide Manager
  -> IMAGE_GUIDES

LTX 2.3 Apply Image Guides, low-resolution stage
LTX 2.3 Apply Image Guides, high-resolution stage
```

Both Apply nodes should receive the same `IMAGE_GUIDES` output. This avoids
adding the same guide images twice by hand.

The Apply node keeps stage-specific settings:

```text
width
height
half_size_first_pass
latent, optional
start_images, optional
```

The Manager owns shared guide behavior:

```text
fps
num_frames
timing_mode
resize_mode
duplicate_policy
pad_color
img_compression
global_strength
start_images_strength
```

Use `half_size_first_pass` only on the stage where the node should create a
half-size latent itself. If you connect an existing latent into Apply, that
latent shape is authoritative and `half_size_first_pass` does not resize it.

## Node Reference

### LTX 2.3 Image Guides (All-in-One)

This node combines the guide manager UI and native guide application in one
node.

Inputs:

```text
positive: CONDITIONING
negative: CONDITIONING
vae: VAE
width: INT
height: INT
fps: FLOAT
num_frames: INT
timing_mode: frame | seconds
resize_mode: contain | pad | stretch | crop
duplicate_policy: error | keep_first | keep_last | offset_next
pad_color: STRING
img_compression: INT
half_size_first_pass: BOOLEAN
global_strength: FLOAT
guides_json: hidden STRING
latent: optional LATENT
start_images: optional IMAGE
start_images_strength: FLOAT
```

Outputs:

```text
positive: CONDITIONING
negative: CONDITIONING
latent: LATENT
```

Use this node when you want a compact single-node setup or when updating older
workflows that already use the original all-in-one node.

### LTX 2.3 Image Guide Manager

This node stores the guide list and shared guide settings. It does not encode
guides by itself. It outputs a reusable `IMAGE_GUIDES` payload for one or more
Apply nodes.

Inputs:

```text
fps: FLOAT
num_frames: INT
timing_mode: frame | seconds
resize_mode: contain | pad | stretch | crop
duplicate_policy: error | keep_first | keep_last | offset_next
pad_color: STRING
img_compression: INT
global_strength: FLOAT
start_images_strength: FLOAT
width: INT
height: INT
guides_json: hidden STRING
```

Output:

```text
image_guides: IMAGE_GUIDES
```

The `width` and `height` values on the Manager are used for preview and aspect
ratio warnings. The Apply node's `width` and `height` are used for actual guide
encoding at that sampler stage.

### LTX 2.3 Apply Image Guides

This node applies an `IMAGE_GUIDES` payload to one sampler stage.

Inputs:

```text
positive: CONDITIONING
negative: CONDITIONING
vae: VAE
width: INT
height: INT
half_size_first_pass: BOOLEAN
image_guides: IMAGE_GUIDES
latent: optional LATENT
start_images: optional IMAGE
```

Outputs:

```text
positive: CONDITIONING
negative: CONDITIONING
latent: LATENT
```

Use this node once per sampler stage. In a two-stage workflow, one Apply node
can guide the low-resolution stage and another Apply node can guide the
high-resolution stage from the same Manager.

## Guide UI

The custom frontend UI appears on the all-in-one node and the Image Guide
Manager node.

Toolbar actions:

```text
Add guide image
Add configured folder
Remove configured folder
Refresh folders/images
Save guide set
Load guide set
```

Guide rows show:

```text
enabled checkbox
image filename
position
strength
move up
move down
remove
```

Image previews are hidden by default. Hover over an image name in the guide list
to show the preview panel.

When adding guide images, the image browser supports:

```text
folder selection
folder-only or recursive subfolder listing
hover-hidden image thumbnails
toggle to keep thumbnails visible
grid column slider
Ctrl-click image for a large preview
click outside large preview or close icon to close
```

## Guide Items

Each manual guide item is stored in workflow JSON as folder alias plus filename,
not as an absolute file path.

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

The backend treats this data as untrusted and validates folder aliases,
filenames, extensions, and final resolved paths.

## Folder Configuration

Configured image folders are stored in:

```text
config/folders.json
```

Each folder has a user-friendly alias. Workflows store the alias and filename so
absolute local paths are not embedded in the workflow JSON.

Supported image extensions:

```text
.png
.jpg
.jpeg
.webp
.bmp
```

The server rejects unknown aliases, unsupported extensions, unsafe paths, and
directory traversal.

## Guide Sets

Guide sets can be saved and loaded from the node UI.

They are stored in:

```text
config/guide_sets/
```

A guide set can include:

```text
guide items
folder aliases
timing mode
fps
width and height metadata
shared guide settings
```

If folders or images are missing when a guide set is loaded, the UI and backend
handle that gracefully with warnings or validation errors instead of silently
using an unsafe path.

## Timing and Frame Counts

Native LTXV guide placement uses pixel frame indexes.

Timing behavior:

```text
timing_mode = frame:
  frame = round(position)

timing_mode = seconds:
  frame = round(position * fps)
```

Negative manual positions count from the end:

```text
-1 = final pixel frame
-2 = second-to-last pixel frame
```

The frame is clamped to:

```text
0..num_frames-1
```

Native LTXV video lengths should be `8*n + 1` pixel frames:

```text
97
105
113
121
...
```

The latent relation is:

```text
latent_frames = ((pixel_frames - 1) // 8) + 1
pixel_frames = (latent_frames - 1) * 8 + 1
```

When this package creates an empty latent internally, invalid lengths now raise
a clear error instead of silently creating fewer frames.

If you connect an existing latent into Apply or the all-in-one node, the latent
shape determines the actual generated length. In that case, Manager `num_frames`
is used mainly for UI timing, preview, and guide position calculations.

## Duplicate Frame Policy

Manual guides are sorted by calculated frame before application.

If two enabled manual guides resolve to the same frame, `duplicate_policy`
controls the behavior:

```text
error:
  raise an error

keep_first:
  keep the earlier guide and ignore later duplicates

keep_last:
  keep the later guide and remove the earlier duplicate

offset_next:
  move the later duplicate to the next available frame
```

Start image sequence overlap is always an error and is not controlled by
`duplicate_policy`.

## Start Image Sequences

The optional `start_images` input accepts a ComfyUI `IMAGE` batch, usually frames
extracted from a video source.

Behavior:

```text
starts at pixel frame 0
encoded as one native LTXV multi-frame guide
uses start_images_strength * global_strength
uses the same resize and image compression path as manual guides
native LTXV cropping is used for valid 8*n + 1 guide length
```

Manual guide images may still be added later in the timeline, for example an
ending image at `-1`.

If a manual guide resolves to a frame covered by the start image sequence, the
node raises an error such as:

```text
Manual guide ending.png at frame 0 overlaps the start image sequence.
```

## Image Resizing

Images are loaded from disk, converted to RGB, resized to the current target
resolution, converted to ComfyUI image tensors, optionally preprocessed with
native LTXV image compression, and then VAE-encoded as LTXV guides.

Resize modes:

```text
contain:
  preserve aspect ratio, fit inside width x height, pad remaining area

pad:
  alias for contain

stretch:
  force image to exactly width x height

crop:
  preserve aspect ratio, fill target, center-crop overflow
```

Default mode is `contain`, so images are not zoomed or cropped by default.

## Image Compression

`img_compression` uses native ComfyUI LTXV preprocessing from
`comfy_extras.nodes_lt.preprocess`.

Behavior:

```text
0:
  disabled, keep resized image tensor unchanged

1..100:
  apply native LTXV image compression before guide encoding
```

Default:

```text
35
```

This matches the native LTXV preprocessing default used by ComfyUI's LTXV
preprocess node.

## Strength Settings

Manual guide strength is:

```text
global_strength * per_image_strength
```

Start image sequence strength is:

```text
global_strength * start_images_strength
```

The result is clamped to:

```text
0.0..1.0
```

High guide strength can make the video follow the reference more strongly, but
it can also reduce motion freedom. It does not generate audio or lip sync by
itself; audio and lip sync depend on the rest of the LTX/audio workflow.

## Two-Stage Upscale Notes

For native 2x LTX upscale workflows, the low-resolution stage and
high-resolution stage may need different active latent sizes.

Use the split workflow when possible:

```text
one Image Guide Manager
two Apply Image Guides nodes
```

Each Apply node can use its own:

```text
width
height
half_size_first_pass
latent input
```

The Manager keeps the image list and shared timing/strength settings synchronized
across both stages.

Important rule:

```text
If a latent is connected, the connected latent shape wins.
```

That means `half_size_first_pass` only affects internally-created empty latents.
It does not resize a latent that already comes from another node.

## Backend Routes

The frontend extension uses local ComfyUI routes for folder and image management.

Routes are implemented in:

```text
routes.py
```

They support:

```text
listing configured folders
adding folder aliases
removing folder aliases
listing images
serving thumbnails
serving full images for preview
saving guide sets
loading guide sets
listing guide sets
refreshing cached data
```

Path validation is handled server-side.

## Files

```text
__init__.py
  Exports node mappings and WEB_DIRECTORY.

nodes.py
  ComfyUI node classes and schemas.

ltx_native.py
  Native LTXV guide application layer.

guide_models.py
  Guide dataclasses and guides_json parsing.

config_store.py
  Folder config, guide-set paths, alias/path validation.

image_io.py
  Image loading, resizing, tensor conversion, thumbnails.

routes.py
  aiohttp routes for the frontend extension.

web/ltx_multi_image_latent_guide.js
  ComfyUI frontend extension and guide UI.

config/folders.json
  Runtime folder aliases.

config/guide_sets/
  Runtime saved guide sets.

thumbnail_cache/
  Runtime thumbnail cache.
```

## Installation

Clone the repository into ComfyUI's `custom_nodes` directory:

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/helto4real/comfui-helto-ltx.git
```

Example for the local development path used by this project:

```bash
cd /home/thhel/git/ComfyUI/custom_nodes
git clone https://github.com/helto4real/comfui-helto-ltx.git
```

Restart ComfyUI after installing or after changing backend Python files.

## Validation

Lightweight syntax checks:

```bash
python -B -m py_compile __init__.py guide_models.py config_store.py image_io.py ltx_native.py nodes.py routes.py
node --check web/ltx_multi_image_latent_guide.js
```

Full validation should be done inside the real ComfyUI instance:

```text
restart ComfyUI
check startup logs
load a workflow
confirm node UI appears
run a short LTXV generation
confirm LTXVCropGuides removes appended guide frames
```

## Troubleshooting

### The generated video has the wrong frame count

Use a native LTXV length of `8*n + 1`, for example `97`, `105`, or `113`.

If an existing latent is connected, check the upstream latent node. The connected
latent determines the actual generated frame count.

### The final image guide does not land on the final frame

Use frame position:

```text
-1
```

Make sure `num_frames` matches the active latent/video length. If a connected
latent has a different length than the Manager, the latent length is the actual
runtime length.

### The output contains extra guide frames

Add native `LTXVCropGuides` after sampling. Guide latents are appended by native
LTXV guide logic and must be cropped where the downstream workflow expects the
normal video latent.

### The Apply node still shows old inputs

ComfyUI can keep stale node interface data in existing workflows after a node
schema changes. Refresh the browser, restart ComfyUI, or recreate the node if
the visual sockets do not update.

The Apply node accepts legacy extra inputs at runtime so old workflows are less
likely to crash while being migrated.

### Thumbnails or image lists are stale

Use the refresh button in the guide toolbar. If needed, restart ComfyUI to clear
server-side state.

### Missing folders or images in a guide set

Re-add the folder alias or update the guide set. Workflows intentionally store
aliases and filenames instead of absolute paths, so aliases must exist in
`config/folders.json`.
