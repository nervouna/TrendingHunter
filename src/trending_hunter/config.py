from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, cast

import click
import yaml

from trending_hunter.settings import Settings

_ENV_LOADED = False


def _load_dotenv(path: str | Path = ".env") -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = Path(path)
    try:
        text = env_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _resolve_env_vars(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{(\w+)\}", replace, value)


def _coerce_value(value: str, default: object) -> object:
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


def _env_key_to_path(key: str) -> list[str]:
    parts = key.lower().split("_")
    path: list[str] = []
    model: Any = Settings
    index = 0

    while index < len(parts):
        fields = getattr(model, "model_fields", None)
        if not fields:
            path.extend(parts[index:])
            break

        match = None
        for end in range(len(parts), index, -1):
            candidate = "_".join(parts[index:end])
            if candidate in fields:
                match = candidate
                index = end
                break

        if match is None:
            path.extend(parts[index:])
            break

        path.append(match)
        annotation = fields[match].annotation
        model = annotation if hasattr(annotation, "model_fields") else object()

    return path


def _apply_env_overrides(
    cfg: dict[str, Any],
    prefix: str = "TH_",
) -> dict[str, Any]:
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        path = _env_key_to_path(key[len(prefix) :])
        node: dict[str, Any] = cfg
        for part in path[:-1]:
            node = node.setdefault(part, {})
        existing = node.get(path[-1])
        default = _get_model_default(path, existing)
        node[path[-1]] = _coerce_value(value, default) if default is not None else value
    return cfg


def _get_model_default(path: list[str], fallback: object) -> object | None:
    from trending_hunter.settings import Settings

    try:
        model: Any = Settings
        for part in path:
            field = model.model_fields[part]
            annotation = field.annotation
            if hasattr(annotation, "model_fields"):
                model = annotation
            else:
                return field.default if field.default is not None else fallback
        return fallback
    except (KeyError, AttributeError):
        return fallback


def _deep_resolve(obj: object) -> object:
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _deep_resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_resolve(v) for v in obj]
    return obj


def load_config(path: str | Path = "config.yaml") -> Settings:
    _load_dotenv()
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {path}")
    cfg = cast(dict[str, Any], yaml.safe_load(raw))
    cfg = _apply_env_overrides(cfg)
    cfg = cast(dict[str, Any], _deep_resolve(cfg))
    return Settings.model_validate(cfg)
