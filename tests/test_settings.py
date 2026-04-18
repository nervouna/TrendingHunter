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
