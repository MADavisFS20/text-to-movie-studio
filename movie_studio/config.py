"""Config: defaults, overridden by a JSON file, overridden by CLI flags."""
import copy
import json
from pathlib import Path

DEFAULTS = {
    "writer": {
        "provider": "ollama",          # ollama | openai | template | file
        "url": "http://127.0.0.1:11434",
        "model": "qwen-2b-uncensored",  # any model name your server knows
        "api_key": "",
        "temperature": 0.8,
        "timeout_s": 300,
        "scenes": 6,
    },
    "video": {
        "backend": "mock",             # mock | comfyui
        "width": 832,
        "height": 480,
        "fps": 24,
        "min_seconds": 2,
        "max_seconds": 10,
        "style": "cinematic, natural lip motion, realistic room acoustics, subtle camera movement",
        "continuity": True,            # feed each scene's last frame to the next (backend must support it)
    },
    "comfyui": {
        "url": "http://127.0.0.1:8188",
        "workflow": "workflows/workflow_api.json",
        "headers": {},
        "timeout_s": 3600,
        "poll_s": 3,
        "inputs": {},                  # see workflows/README.md
        "frame_rule": {"multiple": 1, "plus": 0},
    },
    "safety": {
        "allow_image_input": False,    # user-supplied first-frame images; off unless you turn it on
    },
}


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"config file not found: {p}")
        _merge(cfg, json.loads(p.read_text()))
    return cfg
