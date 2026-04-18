import os
import tempfile

import yaml

from trending_hunter.config import load_config


def test_load_config_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {"api_key": "test-key", "draft": {"model": "m1"}, "audit": {"model": "m2"}},
        "knowledge_base": {"path": "./reports"},
    }))
    cfg = load_config(str(cfg_file))
    assert cfg["sources"]["github"]["enabled"] is True
    assert cfg["signal_gate"]["min_star_velocity"] == 10.0
    assert cfg["llm"]["api_key"] == "test-key"


def test_load_config_env_var_resolution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-123")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 5.0},
        "llm": {"api_key": "${TEST_API_KEY}", "draft": {"model": "m1"}, "audit": {"model": "m2"}},
        "knowledge_base": {"path": "./reports"},
    }))
    cfg = load_config(str(cfg_file))
    assert cfg["llm"]["api_key"] == "secret-123"


def test_load_config_th_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TH_LLM_DRAFT_MODEL", "overridden-model")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 5.0},
        "llm": {"api_key": "k", "draft": {"model": "original"}, "audit": {"model": "m2"}},
        "knowledge_base": {"path": "./reports"},
    }))
    cfg = load_config(str(cfg_file))
    assert cfg["llm"]["draft"]["model"] == "overridden-model"
