# Workflows

The ComfyUI backend does not ship a workflow, because the right one depends on the video model you
choose. You bring one and tell the backend which inputs to fill.

## 1. Build and test a workflow in ComfyUI
Use your model's own text-to-video(+audio) template. Make sure it ends in a node that **saves a video
file with an audio track** (a "Save Video" style node).

## 2. Export it in API format
In ComfyUI's menu use **Save (API Format)** (you may need to enable dev mode options in settings).
Save it as `workflows/workflow_api.json`. A UI-format file (it has a top-level `"nodes"` list) is
rejected with a clear message.

## 3. Map the inputs
Open the exported JSON. Each top-level key is a node id; each node has `inputs`. Find the ids and
field names for the things you want to control and list them in `comfyui.inputs` in your config:

| key | what it controls | required |
|---|---|---|
| `prompt` | the positive text prompt | yes |
| `seed` | random seed (a new one per scene) | no |
| `width`, `height` | frame size | no |
| `frames` | frame count, from `seconds * fps` (see `frame_rule`) | no |
| `fps`, `seconds` | if your model takes them directly | no |
| `first_frame` | a `LoadImage`-style node's `image` field, enables scene-to-scene continuity | no |
| `negative_prompt` | set the text in `comfyui.negative_prompt` | no |

Example: `"prompt": { "node": "6", "field": "text" }`. If a mapped node or field does not exist in your
workflow, the render stops with an error naming it.

`frame_rule` handles models that need specific frame counts, for example 8n+1:
`{ "multiple": 8, "plus": 1 }` turns 24 frames into 25.

`output_node` is optional; set it to your save node's id if the workflow produces more than one video.

## 4. Check
`python3 -m movie_studio doctor --config config.json`

Keep your workflow free of anything you would not want in a public repo: `workflows/*.json` is
git-ignored by default.
