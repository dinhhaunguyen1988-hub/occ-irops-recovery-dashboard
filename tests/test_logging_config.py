"""Tests for src.logging_config — JSON formatter and idempotent setup."""

import json
import logging

from src.logging_config import JsonFormatter, get_logger, setup_logging


def test_json_formatter_emits_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.custom_field = "abc"
    record.numeric_field = 42

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "hello"
    assert payload["custom_field"] == "abc"
    assert payload["numeric_field"] == 42
    assert "ts" in payload


def test_setup_logging_is_idempotent():
    setup_logging()
    handler_count_first = len(logging.getLogger().handlers)

    setup_logging()
    handler_count_second = len(logging.getLogger().handlers)

    assert handler_count_first == handler_count_second == 1


def test_get_logger_returns_named_logger():
    logger = get_logger("occ.test")
    assert logger.name == "occ.test"
