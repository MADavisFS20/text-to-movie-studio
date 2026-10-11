"""ComfyUI backend, using ComfyUI's documented HTTP routes: POST /prompt, GET /history/{id},
GET /view, POST /upload/image.

You supply a workflow exported with "Save (API Format)" and tell this backend which node inputs to fill
(see workflows/README.md). That keeps the backend independent of any one model.
"""
import copy
import json
import time
import uuid
from pathlib import Path

from .. import http
from .base import Backend, RenderError

VIDEO_EXT = (".mp4", ".webm", ".mov", ".mkv")


def _set(workflow, ref, value, what):
    node, field = str(ref["node"]), ref["field"]
    if node not in workflow:
        raise RenderError(f"workflow has no node {node!r} (needed for {what})")
    inputs = workflow[node].setdefault("inputs", {})
    if field not in inputs and not ref.get("create", False):
        raise RenderError(f"node {node!r} has no input {field!r} (needed for {what}); "
                          "check your 'inputs' mapping against the exported API workflow")
    inputs[field] = value


def _find_output(history_entry, output_node=None):
    outputs = history_entry.get("outputs", {})
    nodes = [str(output_node)] if output_node else list(outputs)
    found = []
    for n in nodes:
        for items in outputs.get(n, {}).values():
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and "filename" in it:
                        found.append(it)
    videos = [f for f in found if f["filename"].lower().endswith(VIDEO_EXT)]
    return videos[0] if videos else None


class ComfyUIBackend(Backend):
    name = "comfyui"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.c = cfg["comfyui"]
        self.base = self.c["url"].rstrip("/")
        self.headers = dict(self.c.get("headers") or {})
        self.mapping = self.c.get("inputs") or {}
        if "prompt" not in self.mapping:
            raise RenderError("comfyui.inputs.prompt is required: say which workflow node/field takes the text prompt")
        wf = Path(self.c["workflow"])
        if not wf.exists():
            raise RenderError(f"workflow file not found: {wf} (export one from ComfyUI with 'Save (API Format)')")
        self.template = json.loads(wf.read_text(encoding="utf-8"))
        if "nodes" in self.template:
            raise RenderError("this workflow is in the UI format; re-export it with 'Save (API Format)'")
        self.supports_first_frame = "first_frame" in self.mapping

    def _frames(self, seconds):
        rule = self.c.get("frame_rule", {})
        n = int(round(seconds * self.cfg["video"]["fps"]))
        m = int(rule.get("multiple", 1))
        return max(1, (n // m) * m + int(rule.get("plus", 0)))

    def _upload(self, path):
        path = Path(path)
        body, ctype = http.multipart({"overwrite": "true"}, {"image": (path.name, path.read_bytes(), "image/png")})
        r = json.loads(http.request("POST", self.base + "/upload/image", body,
                                    {"Content-Type": ctype, **self.headers}, 120))
        return r["name"]

    def render(self, scene, out_path, first_frame=None):
        v, m = self.cfg["video"], self.mapping
        wf = copy.deepcopy(self.template)
        _set(wf, m["prompt"], scene.prompt, "prompt")
        if "negative_prompt" in m and self.c.get("negative_prompt"):
            _set(wf, m["negative_prompt"], self.c["negative_prompt"], "negative_prompt")
        if "seed" in m:
            _set(wf, m["seed"], int(uuid.uuid4().int % (2 ** 32)), "seed")
        for key, val in (("width", v["width"]), ("height", v["height"]), ("fps", v["fps"]),
                         ("frames", self._frames(scene.seconds)), ("seconds", scene.seconds)):
            if key in m:
                _set(wf, m[key], val, key)
        if first_frame is not None and "first_frame" in m:
            _set(wf, m["first_frame"], self._upload(first_frame), "first_frame")

        sent = http.post_json(self.base + "/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex},
                              self.headers, 60)
        if sent.get("node_errors"):
            raise RenderError(f"ComfyUI rejected the workflow: {json.dumps(sent['node_errors'])[:600]}")
        pid = sent["prompt_id"]

        deadline = time.time() + float(self.c["timeout_s"])
        while time.time() < deadline:
            hist = http.get_json(f"{self.base}/history/{http.quote(pid)}", self.headers, 60)
            entry = hist.get(pid)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise RenderError(f"ComfyUI reported an error for scene {scene.id}: "
                                      f"{json.dumps(status.get('messages', ''))[:500]}")
                f = _find_output(entry, self.c.get("output_node"))
                if f is None:
                    raise RenderError(f"ComfyUI finished scene {scene.id} but returned no video file; "
                                      "set comfyui.output_node to your video-save node")
                url = (f"{self.base}/view?filename={http.quote(f['filename'])}"
                       f"&subfolder={http.quote(f.get('subfolder', ''))}&type={http.quote(f.get('type', 'output'))}")
                Path(out_path).write_bytes(http.request("GET", url, None, self.headers, 600))
                return out_path
            time.sleep(float(self.c["poll_s"]))
        raise RenderError(f"timed out after {self.c['timeout_s']}s waiting for scene {scene.id}")
