import yaml

from trending_hunter.settings import Settings


def test_load_config_missing_file(tmp_path):
    import pytest

    from trending_hunter.config import load_config

    with pytest.raises(Exception, match="Config file not found"):
        load_config(str(tmp_path / "nonexistent.yaml"))


def test_load_settings_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 10.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
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
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "${TEST_API_KEY}", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.api_key == "secret-123"


def test_load_settings_th_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TH__LLM__DRAFT__MODEL", "overridden-model")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "original"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.model == "overridden-model"


def test_load_settings_legacy_th_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TH_LLM_DRAFT_MODEL", "legacy-model")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "original"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.model == "legacy-model"


def test_load_settings_th_env_override_compound_field(tmp_path, monkeypatch):
    monkeypatch.setenv("TH__LLM__DRAFT__BASE_URL", "https://llm.example.com")
    monkeypatch.setenv("TH__SOURCES__PRODUCT_HUNT__TOP_N", "7")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {
                    "github": {"enabled": True},
                    "product_hunt": {"top_n": 20},
                },
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "original"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.base_url == "https://llm.example.com"
    assert settings.sources.product_hunt.top_n == 7


def test_load_settings_legacy_th_env_override_compound_field(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("TH_LLM_DRAFT_BASE_URL", "https://legacy.example.com")
    monkeypatch.setenv("TH_SOURCES_PRODUCT_HUNT_TOP_N", "9")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {
                    "github": {"enabled": True},
                    "product_hunt": {"top_n": 20},
                },
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "original"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.base_url == "https://legacy.example.com"
    assert settings.sources.product_hunt.top_n == 9


def test_load_settings_th_env_override_bool(tmp_path, monkeypatch):
    monkeypatch.setenv("TH__SOURCES__GITHUB__ENABLED", "false")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.sources.github.enabled is False


def test_load_settings_legacy_th_env_override_bool(tmp_path, monkeypatch):
    monkeypatch.setenv("TH_SOURCES_GITHUB_ENABLED", "false")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.sources.github.enabled is False


def test_double_underscore_env_override_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("TH_LLM_DRAFT_MODEL", "legacy-model")
    monkeypatch.setenv("TH__LLM__DRAFT__MODEL", "explicit-model")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "original"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.model == "explicit-model"


def test_load_settings_th_env_override_int():
    from trending_hunter.config import _coerce_value

    assert _coerce_value("180", 365) == 180
    assert isinstance(_coerce_value("180", 365), int)
    assert _coerce_value("3.14", 1.0) == 3.14
    assert isinstance(_coerce_value("3.14", 1.0), float)
    assert _coerce_value("hello", "") == "hello"


def test_env_override_underscore_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("TH__SIGNAL_GATE__MIN_STAR_VELOCITY", "99.0")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 5.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.signal_gate.min_star_velocity == 99.0


def test_load_settings_model_pricing(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 10.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
                "model_pricing": {
                    "draft": {
                        "input_per_million": 0.80,
                        "output_per_million": 4.00,
                    },
                    "audit": {
                        "input_per_million": 3.00,
                        "output_per_million": 15.00,
                    },
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.model_pricing["draft"].input_per_million == 0.80
    assert settings.model_pricing["audit"].output_per_million == 15.00


def test_load_settings_llm_timeout(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 10.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1", "timeout": 300.0},
                    "audit": {"api_key": "k", "model": "m2"},
                },
            }
        )
    )
    from trending_hunter.config import load_config

    settings = load_config(str(cfg_file))
    assert settings.llm.draft.timeout == 300.0
    assert settings.llm.audit.timeout == 120.0


def test_load_settings_llm_max_tool_rounds(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "sources": {"github": {"enabled": True}},
        "signal_gate": {"min_star_velocity": 10.0},
        "llm": {
            "draft": {"api_key": "k", "model": "m1"},
            "audit": {"api_key": "k", "model": "m2", "max_tool_rounds": 10},
        },
    }))
    from trending_hunter.config import load_config
    settings = load_config(str(cfg_file))
    assert settings.llm.audit.max_tool_rounds == 10
    assert settings.llm.draft.max_tool_rounds == 8


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
    cfg_file.write_text(
        yaml.dump(
            {
                "sources": {"github": {"enabled": True}},
                "signal_gate": {"min_star_velocity": 10.0},
                "llm": {
                    "draft": {"api_key": "k", "model": "m1"},
                    "audit": {"api_key": "k", "model": "m2"},
                },
                "proxy": "",
            }
        )
    )
    import yaml as _yaml

    import trending_hunter.config as cfg

    raw = _yaml.safe_load(cfg_file.read_text())
    resolved = cfg._deep_resolve(raw)
    assert isinstance(resolved, dict)
    assert resolved["sources"]["github"]["enabled"] is True


def test_deep_resolve_list_items():
    import trending_hunter.config as cfg

    result = cfg._deep_resolve(["${HOME}", "plain"])
    assert isinstance(result, list)
    assert result[1] == "plain"
