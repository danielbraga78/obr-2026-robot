from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default.yaml"


def load_config(path: str | None = None) -> Dict[str, Any]:
    config_path = Path(path or DEFAULT_CONFIG_PATH)
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
