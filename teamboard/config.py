"""YAML configs. A config may name a `base:` file; its own values are merged on top of that base."""

import os
from pathlib import Path

import yaml


def deep_merge(base: dict, override: dict) -> dict:
    """Nested dicts are merged key by key; any other value (including lists) replaces the base value."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path) -> dict:
    path = Path(path)
    cfg = yaml.safe_load(path.read_text())
    if "base" in cfg:
        cfg = deep_merge(load_config(path.parent / cfg.pop("base")), cfg)
    return cfg


def apply_env(cfg: dict) -> None:
    os.environ.update({key: str(value) for key, value in cfg.get("env", {}).items()})
