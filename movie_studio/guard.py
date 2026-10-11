"""Content guard. Runs on the user's idea, on every generated scene, and on the final render prompt.

This is a keyword/number layer, NOT a complete moderation system. Anyone hosting this for other
people must add a real moderation model, logging and a reporting channel (see README, "Safety").
"""
import re

MINOR_TERMS = re.compile(
    r"\b(child|children|kid|kids|minor|minors|underage|under-age|preteen|pre-teen|tween|toddler|"
    r"infant|newborn|schoolgirl|schoolboy|school\s?girl|school\s?boy|loli|lolita|shota|jailbait|"
    r"teen|teens|teenage|teenager|juvenile|youngster|boyish|girlish|prepubescent|pubescent)\b",
    re.IGNORECASE,
)
YEARS_OLD = re.compile(r"\b(\d{1,2})[\s-]*(?:years?|yrs?|y/?o)[\s-]*old\b", re.IGNORECASE)
AGE_LABEL = re.compile(r"\bage[d]?\s*[:=]?\s*(\d{1,2})\b", re.IGNORECASE)
GRADE = re.compile(r"\b(?:\d{1,2}(?:st|nd|rd|th)[\s-]grade|high[\s-]school(?:er)?|middle[\s-]school(?:er)?)\b", re.IGNORECASE)
REAL_PERSON = re.compile(
    r"\b(in\s+the\s+likeness\s+of|deepfake|face[\s-]?swap|photo\s+of\s+(?:my|a\s+real))\b",
    re.IGNORECASE,
)

MIN_AGE = 18


class GuardError(ValueError):
    """Raised when text or a plan is refused. The message says why, without echoing the text."""


def check_text(text, label="text"):
    if not text:
        return
    m = MINOR_TERMS.search(text)
    if m:
        raise GuardError(f"{label}: refused, mentions a minor or youthful-coded term ({m.group(0).lower()!r}). "
                         "Every character must be an adult.")
    for rx in (YEARS_OLD, AGE_LABEL):
        for hit in rx.finditer(text):
            if int(hit.group(1)) < MIN_AGE:
                raise GuardError(f"{label}: refused, states an age under {MIN_AGE}.")
    if GRADE.search(text):
        raise GuardError(f"{label}: refused, school-age setting. Every character must be an adult.")
    if REAL_PERSON.search(text):
        raise GuardError(f"{label}: refused, asks for a real person's likeness or a face swap. "
                         "Use fictional characters only.")


def check_age(age, label="character"):
    if isinstance(age, bool) or not isinstance(age, int):
        raise GuardError(f"{label}: age must be a whole number.")
    if age < MIN_AGE:
        raise GuardError(f"{label}: refused, age {age} is under {MIN_AGE}.")
    if age > 120:
        raise GuardError(f"{label}: age {age} is not plausible.")
