import json
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from movie_studio import config, guard, pipeline, scenes, stitch, writer
from movie_studio.backends import RenderError, get_backend
from movie_studio.backends.mock import MockBackend

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

PLAN = {
    "title": "Club Night",
    "characters": [{"name": "Ana", "age": 34, "look": "short dark hair, red jacket"}],
    "scenes": [
        {"setting": "a jazz club", "action": "Ana sings", "dialogue": "One more song.", "seconds": 2},
        {"setting": "backstage", "action": "Ana packs her bag", "seconds": 2},
        {"setting": "the street", "action": "Ana walks into the rain", "seconds": 2},
    ],
}


def serve(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def cfg_for(tmp, **over):
    cfg = config.load()
    cfg["writer"]["provider"] = "template"
    cfg["video"].update(width=160, height=96, fps=12, min_seconds=1)
    for k, v in over.items():
        cfg[k].update(v)
    return cfg


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not installed")
class MockEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_plan_render_and_final_has_video_and_audio(self):
        cfg = cfg_for(self.tmp)
        run = self.tmp / "run"
        (run).mkdir()
        (run / "plan.json").write_text(json.dumps(PLAN))
        final = pipeline.render(run, cfg, log=lambda *_: None)
        s = stitch.streams(final)
        self.assertTrue(s["video"] and s["audio"])
        self.assertAlmostEqual(s["duration"], 6.0, delta=0.6)
        m = json.loads((run / "manifest.json").read_text())
        self.assertTrue(m["has_video"] and m["has_audio"])
        self.assertEqual(len(m["clips"]), 3)
        self.assertTrue((run / "frames" / "scene_001_last.png").exists())

    def test_template_writer_to_movie(self):
        cfg = cfg_for(self.tmp)
        cfg["writer"]["scenes"] = 2
        run = self.tmp / "run2"
        pipeline.make_plan("A lighthouse keeper wakes. A storm arrives.", cfg, run)
        final = pipeline.render(run, cfg, log=lambda *_: None)
        self.assertTrue(stitch.streams(final)["audio"])

    def test_resume_reuses_clips(self):
        cfg = cfg_for(self.tmp)
        run = self.tmp / "run3"
        run.mkdir()
        (run / "plan.json").write_text(json.dumps(PLAN))
        pipeline.render(run, cfg, log=lambda *_: None)
        logs = []
        pipeline.render(run, cfg, log=logs.append)
        self.assertEqual(sum("reusing" in l for l in logs), 3)

    def test_edited_plan_with_minor_is_refused_before_rendering(self):
        cfg = cfg_for(self.tmp)
        run = self.tmp / "run4"
        run.mkdir()
        bad = json.loads(json.dumps(PLAN))
        bad["scenes"][1]["action"] = "a 14-year-old packs a bag"
        (run / "plan.json").write_text(json.dumps(bad))
        with self.assertRaises(guard.GuardError):
            pipeline.render(run, cfg, log=lambda *_: None)
        self.assertFalse((run / "clips").exists())

    def test_first_frame_is_off_by_default(self):
        cfg = cfg_for(self.tmp)
        run = self.tmp / "run5"
        run.mkdir()
        (run / "plan.json").write_text(json.dumps(PLAN))
        img = self.tmp / "a.png"
        img.write_bytes(b"x")
        with self.assertRaises(PermissionError):
            pipeline.render(run, cfg, str(img), True, log=lambda *_: None)
        cfg["safety"]["allow_image_input"] = True
        with self.assertRaises(PermissionError):  # still needs the explicit confirmation
            pipeline.render(run, cfg, str(img), False, log=lambda *_: None)


class FakeOllama(BaseHTTPRequestHandler):
    replies = []
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.seen.append((self.path, body))
        content = FakeOllama.replies.pop(0)
        out = json.dumps({"message": {"content": content}} if self.path == "/api/chat"
                         else {"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class WriterTests(unittest.TestCase):
    def setUp(self):
        FakeOllama.replies, FakeOllama.seen = [], []
        self.srv, self.url = serve(FakeOllama)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def cfg(self, provider):
        c = config.load()
        c["writer"].update(provider=provider, url=self.url, scenes=3)
        return c

    def test_ollama_retries_bad_json_then_succeeds(self):
        FakeOllama.replies = ["not json at all", "```json\n" + json.dumps(PLAN) + "\n```"]
        plan = writer.write_plan("a club night", self.cfg("ollama"))
        self.assertEqual(len(plan.scenes), 3)
        self.assertEqual(len(FakeOllama.seen), 2)
        path, body = FakeOllama.seen[0]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(body["format"], "json")
        self.assertIn("ADULT", body["messages"][0]["content"])
        self.assertIn("Write exactly 3 scenes", body["messages"][0]["content"])

    def test_openai_provider(self):
        FakeOllama.replies = [json.dumps(PLAN)]
        plan = writer.write_plan("a club night", self.cfg("openai"))
        self.assertEqual(FakeOllama.seen[0][0], "/v1/chat/completions")
        self.assertEqual(plan.title, "Club Night")

    def test_model_output_with_minor_is_refused_after_retries(self):
        bad = json.loads(json.dumps(PLAN))
        bad["characters"][0]["age"] = 15
        FakeOllama.replies = [json.dumps(bad)] * 3
        with self.assertRaises(guard.GuardError):
            writer.write_plan("a club night", self.cfg("ollama"))

    def test_idea_with_minor_never_reaches_the_model(self):
        with self.assertRaises(guard.GuardError):
            writer.write_plan("two kids in a kitchen", self.cfg("ollama"))
        self.assertEqual(FakeOllama.seen, [])


class FakeComfy(BaseHTTPRequestHandler):
    clip = b""
    prompts = []
    uploads = []
    polls = 0
    node_errors = {}

    def _json(self, obj, code=200):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        raw = self.rfile.read(n)
        if self.path == "/prompt":
            body = json.loads(raw)
            FakeComfy.prompts.append(body["prompt"])
            self._json({"prompt_id": f"p{len(FakeComfy.prompts)}", "node_errors": FakeComfy.node_errors})
        elif self.path == "/upload/image":
            FakeComfy.uploads.append(len(raw))
            self._json({"name": "uploaded.png"})

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            FakeComfy.polls += 1
            if FakeComfy.polls % 2 == 1:  # first poll: not finished yet
                return self._json({})
            self._json({pid: {"status": {"status_str": "success"},
                              "outputs": {"9": {"images": [{"filename": "x.mp4", "subfolder": "", "type": "output"}]},
                                          "4": {"images": [{"filename": "preview.png", "subfolder": "", "type": "temp"}]}}}})
        elif self.path.startswith("/view"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(FakeComfy.clip)

    def log_message(self, *a):
        pass


WORKFLOW = {
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
    "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 8}},
    "5": {"class_type": "EmptyLatent", "inputs": {"width": 1, "height": 1, "length": 1}},
    "12": {"class_type": "LoadImage", "inputs": {"image": "example.png"}},
    "9": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "ms"}},
}
MAPPING = {
    "prompt": {"node": "6", "field": "text"}, "seed": {"node": "3", "field": "seed"},
    "width": {"node": "5", "field": "width"}, "height": {"node": "5", "field": "height"},
    "frames": {"node": "5", "field": "length"}, "first_frame": {"node": "12", "field": "image"},
}


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not installed")
class ComfyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        sc = scenes.Scene(1, "s", "a", seconds=2)
        sc.prompt = "A jazz duo plays."
        clip = self.tmp / "seed.mp4"
        MockBackend(config.load()).render(scenes.Scene(1, "s", "a", seconds=1), clip)
        FakeComfy.clip, FakeComfy.prompts, FakeComfy.uploads = clip.read_bytes(), [], []
        FakeComfy.polls, FakeComfy.node_errors = 0, {}
        self.srv, self.url = serve(FakeComfy)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        wf = self.tmp / "wf.json"
        wf.write_text(json.dumps(WORKFLOW))
        self.cfg = cfg_for(self.tmp, video={"backend": "comfyui", "width": 160, "height": 96, "fps": 12},
                           comfyui={"url": self.url, "workflow": str(wf), "inputs": MAPPING, "poll_s": 0.05,
                                    "timeout_s": 20, "frame_rule": {"multiple": 8, "plus": 1}})
        self.scene = sc

    def test_fills_workflow_polls_and_downloads_the_video_not_the_preview(self):
        b = get_backend(self.cfg)
        out = b.render(self.scene, self.tmp / "out.mp4")
        s = stitch.streams(out)
        self.assertTrue(s["video"] and s["audio"])
        sent = FakeComfy.prompts[0]
        self.assertEqual(sent["6"]["inputs"]["text"], "A jazz duo plays.")
        self.assertEqual((sent["5"]["inputs"]["width"], sent["5"]["inputs"]["height"]), (160, 96))
        self.assertEqual(sent["5"]["inputs"]["length"], 25)  # 2s*12fps=24 -> 8n+1 = 25
        self.assertEqual(sent["12"]["inputs"]["image"], "example.png")  # untouched without a first frame
        self.assertGreaterEqual(FakeComfy.polls, 2)

    def test_first_frame_is_uploaded_and_wired(self):
        img = self.tmp / "f.png"
        img.write_bytes(b"\x89PNG fake")
        get_backend(self.cfg).render(self.scene, self.tmp / "o.mp4", img)
        self.assertEqual(FakeComfy.prompts[0]["12"]["inputs"]["image"], "uploaded.png")
        self.assertEqual(len(FakeComfy.uploads), 1)

    def test_full_pipeline_through_comfy_backend(self):
        run = self.tmp / "run"
        run.mkdir()
        (run / "plan.json").write_text(json.dumps(PLAN))
        final = pipeline.render(run, self.cfg, log=lambda *_: None)
        s = stitch.streams(final)
        self.assertTrue(s["video"] and s["audio"])
        # scenes 2 and 3 received the previous scene's last frame via upload
        self.assertEqual(len(FakeComfy.uploads), 2)

    def test_node_errors_and_bad_mapping_are_reported(self):
        FakeComfy.node_errors = {"6": {"errors": ["bad"]}}
        with self.assertRaises(RenderError):
            get_backend(self.cfg).render(self.scene, self.tmp / "o.mp4")
        FakeComfy.node_errors = {}
        self.cfg["comfyui"]["inputs"] = dict(MAPPING, seed={"node": "3", "field": "nope"})
        with self.assertRaises(RenderError):
            get_backend(self.cfg).render(self.scene, self.tmp / "o.mp4")

    def test_ui_format_workflow_is_rejected(self):
        wf = self.tmp / "ui.json"
        wf.write_text(json.dumps({"nodes": [], "links": []}))
        self.cfg["comfyui"]["workflow"] = str(wf)
        with self.assertRaises(RenderError):
            get_backend(self.cfg)


if __name__ == "__main__":
    unittest.main()
