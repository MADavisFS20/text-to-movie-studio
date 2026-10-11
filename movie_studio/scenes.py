"""Plan data model, parsing of LLM JSON, and the final render prompt."""
import json
import re
from dataclasses import dataclass, field, asdict

from . import guard


@dataclass
class Character:
    name: str
    age: int
    look: str = ""


@dataclass
class Scene:
    id: int
    setting: str
    action: str
    dialogue: str = ""
    sound: str = ""
    camera: str = ""
    seconds: int = 5
    prompt: str = ""  # filled by compose_prompt


@dataclass
class Plan:
    title: str
    characters: list = field(default_factory=list)
    scenes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(
            title=d.get("title", "Untitled"),
            characters=[Character(**c) for c in d.get("characters", [])],
            scenes=[Scene(**s) for s in d.get("scenes", [])],
        )


class PlanError(ValueError):
    pass


def extract_json(text):
    """Pull the first JSON object out of an LLM reply (handles ```json fences and chatter)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise PlanError("the model did not return a JSON object")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise PlanError(f"the model returned invalid JSON: {e}") from e


def parse_plan(data, min_s=2, max_s=10, max_scenes=30):
    if isinstance(data, str):
        data = extract_json(data)
    if not isinstance(data, dict):
        raise PlanError("plan must be a JSON object")
    chars = data.get("characters")
    scenes = data.get("scenes")
    if not isinstance(chars, list) or not chars:
        raise PlanError("plan needs at least one character, each with a name and an age")
    if not isinstance(scenes, list) or not scenes:
        raise PlanError("plan needs at least one scene")
    if len(scenes) > max_scenes:
        raise PlanError(f"plan has {len(scenes)} scenes, the limit is {max_scenes}")

    characters = []
    for i, c in enumerate(chars, 1):
        if not isinstance(c, dict) or not str(c.get("name", "")).strip():
            raise PlanError(f"character {i} needs a name")
        age = c.get("age")
        if isinstance(age, str) and age.strip().isdigit():
            age = int(age.strip())
        guard.check_age(age, f"character {c.get('name')!r}")
        look = str(c.get("look", "")).strip()
        guard.check_text(look, f"character {c.get('name')!r} look")
        characters.append(Character(str(c["name"]).strip(), age, look))

    out = []
    for i, s in enumerate(scenes, 1):
        if not isinstance(s, dict):
            raise PlanError(f"scene {i} must be an object")
        action = str(s.get("action", "")).strip()
        setting = str(s.get("setting", "")).strip()
        if not action:
            raise PlanError(f"scene {i} needs an action")
        try:
            secs = int(s.get("seconds", 5))
        except (TypeError, ValueError):
            secs = 5
        secs = max(min_s, min(max_s, secs))
        out.append(Scene(
            id=i, setting=setting, action=action,
            dialogue=str(s.get("dialogue", "")).strip(),
            sound=str(s.get("sound", "")).strip(),
            camera=str(s.get("camera", "")).strip(),
            seconds=secs,
        ))
    plan = Plan(title=str(data.get("title", "Untitled")).strip() or "Untitled",
                characters=characters, scenes=out)
    return plan


def compose_prompt(plan, scene, style=""):
    """One descriptive paragraph per scene: visuals, spoken line, sound. This is what the renderer sees."""
    cast = "; ".join(f"{c.name}, {c.age}, {c.look}".rstrip(", ") for c in plan.characters)
    parts = []
    if scene.camera:
        parts.append(scene.camera.rstrip(".") + ".")
    if scene.setting:
        parts.append(scene.setting.rstrip(".") + ".")
    parts.append(scene.action.rstrip(".") + ".")
    if scene.dialogue:
        parts.append(f'Spoken line, with natural lip motion: "{scene.dialogue}"')
    if scene.sound:
        parts.append(f"Sound: {scene.sound.rstrip('.')}.")
    if cast:
        parts.append(f"Characters (all adults): {cast}.")
    if style:
        parts.append(style.rstrip(".") + ".")
    return " ".join(parts)


def finalize(plan, style=""):
    """Compose each scene's render prompt and run the guard over the exact text the renderer will get."""
    for s in plan.scenes:
        s.prompt = compose_prompt(plan, s, style)
        guard.check_text(s.prompt, f"scene {s.id}")
    return plan
