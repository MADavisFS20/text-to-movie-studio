import unittest

from movie_studio import guard, scenes


class GuardTests(unittest.TestCase):
    def test_allows_ordinary_adult_story(self):
        guard.check_text("A jazz duo plays in a softly lit club. The singer, 34, smiles at the pianist.")
        guard.check_text("The sky looks like rain. She says: baby, let's go.")

    def test_refuses_minor_terms(self):
        for t in ["a teenage girl walks home", "two kids in a kitchen", "a schoolgirl", "loli character"]:
            with self.assertRaises(guard.GuardError, msg=t):
                guard.check_text(t)

    def test_refuses_under_18_ages(self):
        for t in ["a 17-year-old pilot", "she is 16 years old", "Age: 15", "aged 12"]:
            with self.assertRaises(guard.GuardError, msg=t):
                guard.check_text(t)
        guard.check_text("a 18-year-old soldier")  # 18 is the floor

    def test_refuses_school_and_likeness(self):
        for t in ["in the 9th grade", "a high school hallway", "a deepfake of someone", "face swap this"]:
            with self.assertRaises(guard.GuardError, msg=t):
                guard.check_text(t)

    def test_age_check(self):
        guard.check_age(18)
        for bad in (17, "30", None, True, 200):
            with self.assertRaises(guard.GuardError):
                guard.check_age(bad)

    def test_message_does_not_echo_text(self):
        try:
            guard.check_text("a 12-year-old with a secret phrase xyzzy")
        except guard.GuardError as e:
            self.assertNotIn("xyzzy", str(e))


GOOD = {
    "title": "Club Night",
    "characters": [{"name": "Ana", "age": 34, "look": "short dark hair, red jacket"}],
    "scenes": [
        {"setting": "a jazz club", "action": "Ana sings at the mic", "dialogue": "One more song.",
         "sound": "piano, soft crowd", "camera": "slow push-in", "seconds": 99},
        {"setting": "backstage", "action": "Ana packs her bag", "seconds": 1},
    ],
}


class PlanTests(unittest.TestCase):
    def test_parse_and_clamp(self):
        plan = scenes.parse_plan(GOOD)
        self.assertEqual([s.seconds for s in plan.scenes], [10, 2])
        self.assertEqual([s.id for s in plan.scenes], [1, 2])

    def test_extracts_fenced_json_and_chatter(self):
        import json
        text = "Sure! Here you go:\n```json\n" + json.dumps(GOOD) + "\n```\nEnjoy."
        self.assertEqual(scenes.parse_plan(text).title, "Club Night")

    def test_rejects_minor_character(self):
        bad = dict(GOOD, characters=[{"name": "Kit", "age": 16, "look": "x"}])
        with self.assertRaises(guard.GuardError):
            scenes.parse_plan(bad)

    def test_rejects_missing_age_and_empty_plans(self):
        with self.assertRaises(guard.GuardError):
            scenes.parse_plan(dict(GOOD, characters=[{"name": "Ana", "look": "x"}]))
        with self.assertRaises(scenes.PlanError):
            scenes.parse_plan(dict(GOOD, scenes=[]))
        with self.assertRaises(scenes.PlanError):
            scenes.parse_plan("no json here")

    def test_prompt_contains_scene_and_cast(self):
        plan = scenes.finalize(scenes.parse_plan(GOOD), "cinematic")
        p = plan.scenes[0].prompt
        for needle in ("jazz club", "One more song.", "piano", "Ana, 34", "all adults", "cinematic"):
            self.assertIn(needle, p)

    def test_finalize_guards_edited_plan(self):
        plan = scenes.parse_plan(GOOD)
        plan.scenes[1].action = "a 15-year-old packs a bag"
        with self.assertRaises(guard.GuardError):
            scenes.finalize(plan)


if __name__ == "__main__":
    unittest.main()
