"""idea -> plan.json -> clips -> movie.mp4. Every step writes to the run folder, so a failed run can resume."""
import json
import re
import time
from pathlib import Path

from . import backends, scenes, stitch, writer


def new_run_dir(root, idea):
    slug = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")[:32] or "movie"
    d = Path(root) / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_plan(idea, cfg, run_dir, plan_file=None):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    plan = writer.write_plan(idea, cfg, plan_file)
    (run_dir / "idea.txt").write_text(idea)
    (run_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2))
    return plan


def load_plan(run_dir, cfg):
    data = json.loads((Path(run_dir) / "plan.json").read_text())
    v = cfg["video"]
    plan = scenes.parse_plan(data, min_s=v["min_seconds"], max_s=v["max_seconds"])
    return scenes.finalize(plan, v["style"])  # re-run the guard on exactly what will be rendered


def _clip_ok(path):
    if not Path(path).exists():
        return False
    try:
        s = stitch.streams(path)
    except stitch.FfmpegError:
        return False
    return s["video"] and s["audio"]


def render(run_dir, cfg, first_frame=None, confirm_fictional=False, log=print):
    run_dir = Path(run_dir)
    plan = load_plan(run_dir, cfg)
    backend = backends.get_backend(cfg)

    if first_frame:
        if not cfg["safety"]["allow_image_input"]:
            raise PermissionError("image input is off. Set safety.allow_image_input=true in your config to use --first-frame.")
        if not confirm_fictional:
            raise PermissionError("--first-frame needs --confirm-fictional-subject: the image must show a "
                                  "fictional adult character, never a real person.")
        if not backend.supports_first_frame:
            raise PermissionError(f"backend {backend.name!r} has no first_frame mapping")

    clips_dir = run_dir / "clips"
    frames_dir = run_dir / "frames"
    clips_dir.mkdir(exist_ok=True)
    frames_dir.mkdir(exist_ok=True)
    manifest = {"title": plan.title, "backend": backend.name, "clips": [], "warnings": []}
    clips = []
    prev_frame = Path(first_frame) if first_frame else None

    for scene in plan.scenes:
        clip = clips_dir / f"scene_{scene.id:03d}.mp4"
        if _clip_ok(clip):
            log(f"scene {scene.id}/{len(plan.scenes)}: reusing {clip.name}")
        else:
            log(f"scene {scene.id}/{len(plan.scenes)}: rendering ({scene.seconds}s) with {backend.name}")
            start_frame = prev_frame if (backend.supports_first_frame and
                                         (scene.id == 1 or cfg["video"]["continuity"])) else None
            backend.render(scene, clip, start_frame)
            if not _clip_ok(clip):
                s = stitch.streams(clip)
                if not s["video"]:
                    raise backends.RenderError(f"scene {scene.id}: the backend produced a file with no video stream")
                manifest["warnings"].append(f"scene {scene.id}: no audio stream, silence added")
        clips.append(clip)
        manifest["clips"].append(str(clip.relative_to(run_dir)))
        if cfg["video"]["continuity"] and backend.supports_first_frame:
            prev_frame = stitch.last_frame(clip, frames_dir / f"scene_{scene.id:03d}_last.png")

    v = cfg["video"]
    final = stitch.concat(clips, run_dir / "movie.mp4", run_dir / "work", v["width"], v["height"], v["fps"])
    info = stitch.streams(final)
    manifest.update(final=str(final.relative_to(run_dir)), duration_s=round(info["duration"], 2),
                    has_video=info["video"], has_audio=info["audio"])
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return final
