import argparse
import shutil
import sys
from pathlib import Path

from . import config, guard, pipeline, scenes
from .backends import RenderError
from .http import HttpError
from .stitch import FfmpegError


def _cfg(a):
    cfg = config.load(a.config)
    if getattr(a, "writer", None):
        cfg["writer"]["provider"] = a.writer
    if getattr(a, "backend", None):
        cfg["video"]["backend"] = a.backend
    if getattr(a, "scenes", None):
        cfg["writer"]["scenes"] = a.scenes
    return cfg


def _add_common(p):
    p.add_argument("--config", help="path to a JSON config (see config.example.json)")
    p.add_argument("--writer", choices=["ollama", "openai", "template", "file"], help="override writer.provider")
    p.add_argument("--backend", choices=["mock", "comfyui"], help="override video.backend")
    p.add_argument("--scenes", type=int, help="number of scenes to ask the writer for")
    p.add_argument("--runs", default="runs", help="folder for run output (default: runs)")


def _add_render(p):
    p.add_argument("--first-frame", help="image for scene 1 (off unless safety.allow_image_input is true)")
    p.add_argument("--confirm-fictional-subject", action="store_true",
                   help="confirm the --first-frame image shows a fictional adult, not a real person")


def cmd_plan(a):
    cfg = _cfg(a)
    run = Path(a.out) if a.out else pipeline.new_run_dir(a.runs, a.idea)
    plan = pipeline.make_plan(a.idea, cfg, run, a.plan_file)
    print(f"plan written: {run / 'plan.json'}  ({len(plan.scenes)} scenes). Edit it, then run: render {run}")
    return 0


def cmd_render(a):
    cfg = _cfg(a)
    final = pipeline.render(a.run, cfg, a.first_frame, a.confirm_fictional_subject)
    print(f"movie: {final}")
    return 0


def cmd_make(a):
    cfg = _cfg(a)
    run = Path(a.out) if a.out else pipeline.new_run_dir(a.runs, a.idea)
    pipeline.make_plan(a.idea, cfg, run, a.plan_file)
    final = pipeline.render(run, cfg, a.first_frame, a.confirm_fictional_subject)
    print(f"movie: {final}")
    return 0


def cmd_doctor(a):
    cfg = _cfg(a)
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        found = shutil.which(tool)
        print(f"{tool}: {found or 'MISSING'}")
        ok &= bool(found)
    print(f"writer: {cfg['writer']['provider']} ({cfg['writer']['url']}, model {cfg['writer']['model']})")
    print(f"video backend: {cfg['video']['backend']}")
    if cfg["video"]["backend"] == "comfyui":
        from .backends import get_backend
        try:
            b = get_backend(cfg)
            print(f"comfyui workflow OK, first-frame input: {b.supports_first_frame}")
        except RenderError as e:
            print(f"comfyui: {e}")
            ok = False
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="movie-studio", description="Text to movie: story idea in, MP4 with audio out.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="write plan.json from an idea (no rendering)")
    p.add_argument("idea")
    p.add_argument("--out", help="run folder (default: runs/<timestamp>-<slug>)")
    p.add_argument("--plan-file", help="plan JSON to use with --writer file")
    _add_common(p)
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("render", help="render a run folder's plan.json into movie.mp4 (resumes)")
    p.add_argument("run")
    _add_common(p)
    _add_render(p)
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("make", help="plan + render in one go")
    p.add_argument("idea")
    p.add_argument("--out")
    p.add_argument("--plan-file")
    _add_common(p)
    _add_render(p)
    p.set_defaults(fn=cmd_make)

    p = sub.add_parser("doctor", help="check ffmpeg and your config")
    _add_common(p)
    p.set_defaults(fn=cmd_doctor)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except guard.GuardError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    except (scenes.PlanError, RenderError, FfmpegError, HttpError, PermissionError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
