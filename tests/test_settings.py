import yaml

from trending_hunter.settings import Settings, ModelPricing


def test_load_settings_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {
            "draft": {"api_key": "k", "model": "m1"},
            "audit": {"api_key": "k", "model": "m2"},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert isinstance(settings, Settings)
    assert settings.sources.github.enabled is True
    assert settings.signal_gate.min_star_velocity == 10.0
    assert settings.llm.draft.model == "m1"
    assert settings.llm.audit.model == "m2"
    assert settings.knowledge_base.path == "./reports"


def test_load_settings_env_var_resolution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-123")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 5.0},
        "llm": {
            "draft": {"api_key": "${TEST_API_KEY}", "model": "m1"},
            "audit": {"api_key": "k", "model": "m2"},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert settings.llm.draft.api_key == "secret-123"


def test_load_settings_th_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TH_LLM_DRAFT_MODEL", "overridden-model")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 5.0},
        "llm": {
            "draft": {"api_key": "k", "model": "original"},
            "audit": {"api_key": "k", "model": "m2"},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert settings.llm.draft.model == "overridden-model"


def test_load_settings_model_pricing(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {
            "draft": {"api_key": "k", "model": "m1"},
            "audit": {"api_key": "k", "model": "m2"},
        },
        "model_pricing": {
            "m1": {"input_per_million": 0.80, "output_per_million": 4.00},
            "m2": {"input_per_million": 3.00, "output_per_million": 15.00},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert settings.model_pricing["m1"].input_per_million == 0.80
    assert settings.model_pricing["m2"].output_per_million == 15.00


def test_load_settings_llm_timeout(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {
            "draft": {"api_key": "k", "model": "m1", "timeout": 300.0},
            "audit": {"api_key": "k", "model": "m2"},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert settings.llm.draft.timeout == 300.0
    assert settings.llm.audit.timeout == 120.0


def test_load_dotenv_missing_file(tmp_path, monkeypatch):
    import trending_hunter.config as cfg
    old = cfg._ENV_LOADED
    cfg._ENV_LOADED = False
    try:
        cfg._load_dotenv(str(tmp_path / "nonexistent.env"))
        assert cfg._ENV_LOADED is True
    finally:
        cfg._ENV_LOADED = old


def test_load_dotenv_skips_comments_and_blanks(tmp_path, monkeypatch):
    import trending_hunter.config as cfg
    env_file = tmp_path / ".env"
    env_file.write_text("# comment line\n\n  \nMY_TEST_VAR=hello\n")
    old_loaded = cfg._ENV_LOADED
    old_val = monkeypatch.delenv("MY_TEST_VAR", raising=False)
    cfg._ENV_LOADED = False
    try:
        cfg._load_dotenv(str(env_file))
        import os
        assert os.environ.get("MY_TEST_VAR") == "hello"
    finally:
        cfg._ENV_LOADED = old_loaded
        if old_val is not None:
            monkeypatch.setenv("MY_TEST_VAR", old_val)


def test_load_dotenv_does_not_override_existing(tmp_path, monkeypatch):
    import trending_hunter.config as cfg
    env_file = tmp_path / ".env"
    env_file.write_text("MY_EXISTING_VAR=from_file\n")
    monkeypatch.setenv("MY_EXISTING_VAR", "original")
    old = cfg._ENV_LOADED
    cfg._ENV_LOADED = False
    try:
        cfg._load_dotenv(str(env_file))
        import os
        assert os.environ["MY_EXISTING_VAR"] == "original"
    finally:
        cfg._ENV_LOADED = old


def test_deep_resolve_handles_list(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {
            "draft": {"api_key": "k", "model": "m1"},
            "audit": {"api_key": "k", "model": "m2"},
        },
        "proxy": "",
    }))
    import trending_hunter.config as cfg
    import yaml as _yaml
    raw = _yaml.safe_load(cfg_file.read_text())
    resolved = cfg._deep_resolve(raw)
    assert isinstance(resolved, dict)
    assert resolved["sources"]["github"]["enabled"] is True


def test_deep_resolve_list_items():
    import trending_hunter.config as cfg
    result = cfg._deep_resolve(["${HOME}", "plain"])
    assert isinstance(result, list)
    assert result[1] == "plain"
