import unittest

import game
from ui import config


class ModelMapTests(unittest.TestCase):
    def test_model_labels(self):
        self.assertEqual(config.MODEL_LABELS, ["5M", "23M", "79M"])

    def test_label_model_round_trip(self):
        for label, model in config.MODEL_BY_LABEL.items():
            self.assertEqual(config.LABEL_BY_MODEL[model], label)
            self.assertEqual(config.MODEL_BY_LABEL[config.LABEL_BY_MODEL[model]], model)

    def test_default_engine_path(self):
        path = config.default_engine_path(game.MaiaEngineModel.MAIA3_5M)
        self.assertTrue(path.endswith("maia3-5m.exe"), path)


class StyleNamesTests(unittest.TestCase):
    def test_excludes_off_sentinel_includes_natural(self):
        self.assertNotIn(
            game.PlayingStyles.NOT_USING_PLAYING_STYLE.name, config.STYLE_NAMES
        )
        self.assertIn(game.PlayingStyles.NATURAL.name, config.STYLE_NAMES)


class IsDefaultPathTests(unittest.TestCase):
    def test_empty_is_default(self):
        self.assertTrue(config.is_default_path(""))
        self.assertTrue(config.is_default_path("   "))

    def test_bundled_path_is_default(self):
        bundled = config.default_engine_path(game.MaiaEngineModel.MAIA3_23M)
        self.assertTrue(config.is_default_path(bundled))

    def test_custom_path_is_not_default(self):
        self.assertFalse(config.is_default_path(r"C:\somewhere\my-engine.exe"))


class ResolvePlayerConfigTests(unittest.TestCase):
    def test_custom_enabled_uses_sentinel_and_rounds(self):
        style, temp, topp = config.resolve_player_config(True, 0.4, 0.8, "NATURAL")
        self.assertEqual(style, game.PlayingStyles.NOT_USING_PLAYING_STYLE)
        self.assertEqual(temp, 0.4)
        self.assertEqual(topp, 0.8)

    def test_custom_enabled_rounds_to_two_places(self):
        _, temp, topp = config.resolve_player_config(True, 0.123456, 0.987654, "NATURAL")
        self.assertEqual(temp, 0.12)
        self.assertEqual(topp, 0.99)

    def test_custom_disabled_uses_named_style(self):
        style, temp, topp = config.resolve_player_config(False, 0.4, 0.8, "SOLID")
        self.assertEqual(style, game.PlayingStyles.SOLID)
        self.assertIsNone(temp)
        self.assertIsNone(topp)


if __name__ == "__main__":
    unittest.main()
