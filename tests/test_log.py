import logging

from trending_hunter.log import get_logger, setup_logging


def test_setup_logging_returns_logger():
    logger = setup_logging()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "trending_hunter"


def test_get_logger_returns_same_instance():
    a = get_logger()
    b = get_logger()
    assert a is b


def test_setup_logging_respects_level(monkeypatch):
    monkeypatch.setenv("TH_LOG_LEVEL", "WARNING")
    setup_logging()
    logger = get_logger()
    assert logger.level == logging.WARNING
