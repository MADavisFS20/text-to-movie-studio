"""Scene writer: turns a story idea into a validated Plan.

Providers:
  ollama    local or remote Ollama server (POST /api/chat)
  openai    any OpenAI-compatible server (POST /v1/chat/completions)
  template  offline, deterministic splitter (no LLM). Used for tests and dry runs.
  file      you provide the plan JSON yourself
"""
import json
from pathlib import Path

from . import guard, http, scenes

SYSTEM = """You are a screenwriter for short films made of separate video clips.
Reply with ONE JSON object and nothing else, in this shape:
{"title": str,
 "characters": [{"name": str, "age": int, "look": str}],
 "scenes": [{"setting": str, "action": str, "dialogue": str, "sound": str, "camera": str, "seconds": int}]}
Rules:
- Every character is a fictional ADULT with an explicit integer age of 21 or more. Never write minors.
- Never base a character on a real person.
- Each scene is one continuous shot of {min_s}-{max_s} seconds. Describe only what can be seen and heard.
- "dialogue" is a short spoken line (or empty). "sound" is ambient sound and music. "camera" is shot type and movement.
- Repeat each character's "look" consistently so they stay recognisable between clips.
- Write exactly {n} scenes."""


def _messages(idea, n, min_s, max_s):
    return [
        {"role": "system", "content": SYSTEM.replace("{n}", str(n)).replace("{min_s}", str(min_s)).replace("{max_s}", str(max_s))},
        {"role": "user", "content": f"Story idea: {idea}"},
    ]


def _ollama(cfg, msgs):
    w = cfg["writer"]
    body = {"model": w["model"], "messages": msgs, "stream": False, "format": "json",
            "options": {"temperature": w["temperature"]}}
    r = http.post_json(w["url"].rstrip("/") + "/api/chat", body, timeout=w["timeout_s"])
    return r["message"]["content"]


def _openai(cfg, msgs):
    w = cfg["writer"]
    headers = {"Authorization": f"Bearer {w['api_key']}"} if w.get("api_key") else {}
    body = {"model": w["model"], "messages": msgs, "temperature": w["temperature"]}
    r = http.post_json(w["url"].rstrip("/") + "/v1/chat/completions", body, headers, w["timeout_s"])
    return r["choices"][0]["message"]["content"]


def _template(idea, n):
    """Deterministic fallback: one scene per sentence/clause of the idea, with a placeholder cast."""
    import re
    bits = [b.strip() for b in re.split(r"[.;\n]+", idea) if b.strip()] or [idea.strip()]
    sc = []
    for i in range(n):
        sc.append({"setting": f"Scene {i + 1}", "action": bits[i % len(bits)],
                   "dialogue": "", "sound": "ambient room tone", "camera": "medium shot, steady", "seconds": 3})
    return {"title": bits[0][:60], "characters": [{"name": "Lead", "age": 30, "look": "neutral costume"}],
            "scenes": sc}


def write_plan(idea, cfg, plan_file=None):
    guard.check_text(idea, "idea")
    w, v = cfg["writer"], cfg["video"]
    n = int(w["scenes"])
    kw = dict(min_s=v["min_seconds"], max_s=v["max_seconds"])
    provider = w["provider"]
    if provider == "file":
        if not plan_file:
            raise scenes.PlanError("writer provider 'file' needs --plan-file")
        raw = json.loads(Path(plan_file).read_text(encoding="utf-8"))
    elif provider == "template":
        raw = _template(idea, n)
    elif provider in ("ollama", "openai"):
        fn = _ollama if provider == "ollama" else _openai
        last = None
        for _ in range(3):  # small models often break the JSON; retry
            try:
                raw = scenes.extract_json(fn(cfg, _messages(idea, n, kw["min_s"], kw["max_s"])))
                plan = scenes.parse_plan(raw, **kw, max_scenes=30)
                return scenes.finalize(plan, v["style"])
            except (scenes.PlanError, guard.GuardError, KeyError) as e:
                last = e
        if isinstance(last, guard.GuardError):
            raise last
        raise scenes.PlanError(f"the writer model failed to produce a valid plan after 3 tries: {last}")
    else:
        raise scenes.PlanError(f"unknown writer provider {provider!r}")
    plan = scenes.parse_plan(raw, **kw)
    return scenes.finalize(plan, v["style"])
