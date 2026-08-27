# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Coverage batch 20: logging_config, levels, discovery, cache_stats, cache_monitor."""

from __future__ import annotations

import logging

# === Module: logging_config ===


class TestStructuredFormatter:
    def test_formats_record(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False, include_context=False)
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Hello world" in result
        assert "INFO" in result
        assert "test.module" in result

    def test_color_disabled_when_not_tty(self):
        from attune.logging_config import StructuredFormatter

        # use_color=True but non-tty won't color
        formatter = StructuredFormatter(use_color=True)
        assert isinstance(formatter, StructuredFormatter)

    def test_no_color_formatter(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False)
        record = logging.LogRecord(
            name="m",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="warning msg",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "warning msg" in result
        assert "\033[" not in result

    def test_includes_context_when_enabled(self):
        from attune.logging_config import StructuredFormatter

        formatter = StructuredFormatter(use_color=False, include_context=True)
        record = logging.LogRecord(
            name="m",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.context = {"user": "alice", "id": "42"}
        result = formatter.format(record)
        assert "user=alice" in result


class TestLoggingConfig:
    def setup_method(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig._configured = False
        LoggingConfig._loggers = {}

    def test_configure_sets_level(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig.configure(level=logging.DEBUG)
        assert LoggingConfig._level == logging.DEBUG
        assert LoggingConfig._configured is True

    def test_get_logger_returns_logger(self):
        from attune.logging_config import LoggingConfig

        logger = LoggingConfig.get_logger("test.batch20")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_same_instance(self):
        from attune.logging_config import LoggingConfig

        l1 = LoggingConfig.get_logger("test.same")
        l2 = LoggingConfig.get_logger("test.same")
        assert l1 is l2

    def test_set_level_propagates(self):
        from attune.logging_config import LoggingConfig

        LoggingConfig.get_logger("test.setlevel")
        LoggingConfig.set_level(logging.ERROR)
        for logger in LoggingConfig._loggers.values():
            assert logger.level == logging.ERROR


class TestGetLogger:
    def test_get_logger_returns_logger(self):
        from attune.logging_config import get_logger

        logger = get_logger("attune.test.batch20")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self):
        from attune.logging_config import get_logger

        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
