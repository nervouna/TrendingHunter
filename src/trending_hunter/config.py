from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_ENV_LOADED = False


def _load_dotenv(path: str | Path = ".env") -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _resolve_env_vars(value: str) -> str:
    def replace(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{(\w+)\}", replace, value)


def _apply_env_overrides(cfg: dict, prefix: str = "TH_") -> dict:
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        path = key[len(prefix):].lower().split("_")
        node = cfg
        for part in path[:-1]:
            node = node.setdefault(part, {})
        node[path[-1]] = value
    return cfg


def _deep_resolve(obj: object) -> object:
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _deep_resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_resolve(v) for v in obj]
    return obj


def load_config(path: str | Path = "config.yaml") -> dict[str, object]:
    _load_dotenv()
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    cfg = yaml.safe_load(raw)
    cfg = _apply_env_overrides(cfg)
    cfg = _deep_resolve(cfg)
    return cfg
