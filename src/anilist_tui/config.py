from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_THEME = "catppuccin-mocha"
DEFAULT_BACKGROUND = None
CONFIG_PATH = Path.home() / ".config" / "anilist-tui" / "config.toml"


@dataclass
class AppConfig:
    theme: str = DEFAULT_THEME
    background: str|None = DEFAULT_BACKGROUND


def _default_config_content() -> str:
    return (
        "[ui]\n"
        "theme = \"catppuccin-mocha\"\n"
    )


def ensure_config_exists() -> None:
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_default_config_content(), encoding="utf-8")


def load_app_config() -> AppConfig:
    ensure_config_exists()
    try:
        with CONFIG_PATH.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return AppConfig()

    ui = data.get("ui") if isinstance(data, dict) else None
    if not isinstance(ui, dict):
        return AppConfig()

    theme = ui.get("theme")
    background = ui.get("background")
    if (isinstance(theme, str) and theme.strip()) and background is None:
        return AppConfig(theme=theme.strip(), background=None)
    if (isinstance(theme, str) and theme.strip()) and (isinstance(background, str) and background.strip()):
        return AppConfig(theme=theme.strip(), background=background.strip())

    return AppConfig()
