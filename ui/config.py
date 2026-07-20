"""UI-agnostic glue between ``game.py`` and the desktop UI.

Pure logic only -- no tkinter -- so it can be unit-tested without a display:
engine-path derivation, model/style dropdown maps, and the small decision
helpers the widgets delegate to.
"""

import os

import game

# --- Engine defaults --------------------------------------------------------
# The console app hardcoded the 5M engine under the project's venv. Derive the
# same location relative to the repo root so it works regardless of where the
# repo lives, and expose it as an editable field in the UI.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_SCRIPTS = os.path.join(PROJECT_DIR, ".venv", "Scripts")


def default_engine_path(model: game.MaiaEngineModel) -> str:
    """Path to the bundled Maia executable matching a model (e.g. maia3-5m.exe)."""
    return os.path.join(VENV_SCRIPTS, f"{model.value}.exe")


# Normalized set of the bundled engine paths, used to decide whether the
# engine-path field still holds a "default" we may auto-swap when the model
# changes (vs. a custom path the user typed, which we leave alone).
DEFAULT_ENGINE_PATHS = {
    os.path.normcase(default_engine_path(m)) for m in game.MaiaEngineModel
}

# "MAIA3_5M" -> "5M", keyed for the model dropdown.
MODEL_BY_LABEL = {m.name.replace("MAIA3_", ""): m for m in game.MaiaEngineModel}
MODEL_LABELS = list(MODEL_BY_LABEL.keys())
LABEL_BY_MODEL = {m: label for label, m in MODEL_BY_LABEL.items()}

# Named playing styles the user can pick (everything except the "off" sentinel).
STYLE_NAMES = [
    s.name
    for s in game.PlayingStyles
    if s != game.PlayingStyles.NOT_USING_PLAYING_STYLE
]


def is_default_path(path: str) -> bool:
    """True if ``path`` is empty or one of the bundled engine paths.

    When it is, the model dropdown may replace it with the default path for the
    newly selected model; otherwise the user typed a custom path we leave alone.
    """
    normalized = os.path.normcase(path.strip())
    return normalized == "" or normalized in DEFAULT_ENGINE_PATHS


def resolve_player_config(custom_enabled, temperature, topp, style_name):
    """Map a side's widget state to ``simulate_game``'s per-side arguments.

    Returns ``(playing_style, custom_temperature, custom_topp)``. With custom
    parameters on, the style is the "off" sentinel and the temp/top-p values are
    passed through; otherwise the named style is used and the customs are None.
    """
    if custom_enabled:
        return (
            game.PlayingStyles.NOT_USING_PLAYING_STYLE,
            round(temperature, 2),
            round(topp, 2),
        )
    return game.PlayingStyles[style_name], None, None
