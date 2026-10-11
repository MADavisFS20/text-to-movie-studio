"""Mock renderer: a flat colour clip with a sine tone. For testing the pipeline without a GPU or a model."""
import subprocess

from .base import Backend, RenderError

COLOURS = ["0x2b4c7e", "0x7e2b4c", "0x4c7e2b", "0x7e6b2b", "0x2b7e6b", "0x6b2b7e"]


class MockBackend(Backend):
    name = "mock"
    supports_first_frame = True  # accepted and ignored, so continuity wiring gets exercised

    def render(self, scene, out_path, first_frame=None):
        v = self.cfg["video"]
        colour = COLOURS[(scene.id - 1) % len(COLOURS)]
        freq = 220 + 55 * scene.id
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={colour}:s={v['width']}x{v['height']}:r={v['fps']}:d={scene.seconds}",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=44100:duration={scene.seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out_path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RenderError(f"ffmpeg failed: {r.stderr.strip()[:400]}")
        return out_path
