"""ffmpeg helpers: probe streams, grab a last frame, normalise clips, concatenate into the movie."""
import json
import subprocess
from pathlib import Path


class FfmpegError(RuntimeError):
    pass


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FfmpegError(f"{cmd[0]} failed: {r.stderr.strip()[-500:]}")
    return r.stdout


def probe(path):
    out = _run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(out)


def streams(path):
    info = probe(path)
    kinds = [s.get("codec_type") for s in info.get("streams", [])]
    return {"video": "video" in kinds, "audio": "audio" in kinds,
            "duration": float(info.get("format", {}).get("duration", 0) or 0)}


def last_frame(clip, out_png):
    _run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(clip),
          "-frames:v", "1", "-update", "1", str(out_png)])
    return Path(out_png)


def normalise(clip, out, width, height, fps):
    """Same size, fps, pixel format and audio format for every clip; adds silence if a clip has no audio."""
    s = streams(clip)
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip)]
    if s["audio"]:
        cmd += ["-vf", vf, "-af", "aresample=44100,aformat=channel_layouts=stereo"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", vf, "-shortest"]
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)]
    _run(cmd)
    return Path(out)


def concat(clips, out, work_dir, width, height, fps):
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    norm = [normalise(c, work / f"norm_{i:03d}.mp4", width, height, fps) for i, c in enumerate(clips, 1)]
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in norm), encoding="utf-8")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", "-movflags", "+faststart", str(out)])
    return Path(out)
