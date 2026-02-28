"""Tests for attune.logging_config"""

import logging

from attune.logging_config import (
    LoggingConfig,
    StructuredFormatter,
    create_logger,
    get_logger,
    init_logging_from_env,
)


class TestStructuredFormatter:
    """Tests for StructuredFormatter class."""

    def test_initialization_with_color(self):
        """Test StructuredFormatter initialization with color."""
        formatter = StructuredFormatter(use_color=True, include_context=False)

        assert formatter is not None
        assert formatter.include_context is False

    def test_initialization_without_color(self):
        """Test StructuredFormatter initialization without color."""
        formatter = StructuredFormatter(use_color=False, include_context=True)

        assert formatter is not None
        assert formatter.include_context is True

    def test_format_log_record(self):
        """Test formatting a log record."""
        formatter = StructuredFormatter(use_color=False, include_context=False)

        # Create log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        formatted = formatter.format(record)

        assert "INFO" in formatted
        assert "test_logger" in formatted
        assert "test_function" in formatted
        assert "Test message" in formatted

    def test_format_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter(use_color=False, include_context=False)

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.funcName = "test_function"

        formatted = formatter.format(record)

        assert "ERROR" in formatted
        assert "Error occurred" in formatted
        assert "ValueError" in formatted
        assert "Test error" in formatted


class TestLoggingConfig:
    """Tests for LoggingConfig class."""

    def test_configure_basic(self):
        """Test basic LoggingConfig configuration."""
        # Reset class state
        LoggingConfig._configured = False
        LoggingConfig._loggers.clear()

        LoggingConfig.configure(
            level=logging.DEBUG,
            log_dir=None,
            use_color=True,
            include_context=False,
        )

        assert LoggingConfig._configured is True
        assert LoggingConfig._level == logging.DEBUG
        assert LoggingConfig._use_color is True

    def test_get_logger_basic(self):
        """Test getting a logger from LoggingConfig."""
        # Reset class state
        LoggingConfig._configured = False
        LoggingConfig._loggers.clear()

        logger = LoggingConfig.get_logger("test.module")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_caching(self):
        """Test that get_logger returns cached instances."""
        # Reset class state
        LoggingConfig._configured = False
        LoggingConfig._loggers.clear()

        logger1 = LoggingConfig.get_logger("test.module")
        logger2 = LoggingConfig.get_logger("test.module")

        # Should be same instance
        assert logger1 is logger2

    def test_set_level(self):
        """Test setting logging level for all loggers."""
        # Reset class state
        LoggingConfig._configured = False
        LoggingConfig._loggers.clear()

        logger = LoggingConfig.get_logger("test.module")

        LoggingConfig.set_level(logging.DEBUG)

        assert logger.level == logging.DEBUG


def test_create_logger_basic():
    """Test create_logger with basic configuration."""
    logger = create_logger(
        "test.create_logger",
        level=logging.INFO,
        use_color=False,
    )

    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.create_logger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0


def test_create_logger_with_file(tmp_path):
    """Test create_logger with file logging."""
    log_file = tmp_path / "test.log"

    logger = create_logger(
        "test.file_logger",
        level=logging.DEBUG,
        log_file=str(log_file),
        use_color=False,
    )

    assert logger is not None
    logger.info("Test log message")

    # Verify file was created
    assert log_file.exists()


def test_create_logger_with_log_dir(tmp_path):
    """Test create_logger with log directory."""
    logger = create_logger(
        "test.dir_logger",
        level=logging.DEBUG,
        log_dir=str(tmp_path),
        use_color=False,
    )

    assert logger is not None
    logger.info("Test log message")

    # Verify log file was created in directory
    log_files = list(tmp_path.glob("*.log"))
    assert len(log_files) > 0


def test_create_logger_idempotent():
    """Test that create_logger is idempotent."""
    logger1 = create_logger("test.idempotent", level=logging.INFO)
    logger2 = create_logger("test.idempotent", level=logging.DEBUG)

    # Should return same logger (idempotent)
    assert logger1 is logger2


def test_get_logger_convenience_function():
    """Test get_logger convenience function."""
    logger = get_logger("test.convenience")

    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.convenience"


def test_init_logging_from_env_default(monkeypatch):
    """Test init_logging_from_env with default values."""
    # Reset class state
    LoggingConfig._configured = False
    LoggingConfig._loggers.clear()

    # Clear environment variables
    monkeypatch.delenv("EMPATHY_LOG_LEVEL", raising=False)
    monkeypatch.delenv("EMPATHY_LOG_DIR", raising=False)
    monkeypatch.delenv("EMPATHY_LOG_COLOR", raising=False)
    monkeypatch.delenv("EMPATHY_LOG_CONTEXT", raising=False)

    init_logging_from_env()

    assert LoggingConfig._configured is True
    assert LoggingConfig._level == logging.INFO  # Default
    assert LoggingConfig._use_color is True  # Default


def test_init_logging_from_env_custom(monkeypatch, tmp_path):
    """Test init_logging_from_env with custom environment variables."""
    # Reset class state
    LoggingConfig._configured = False
    LoggingConfig._loggers.clear()

    # Set custom environment variables
    monkeypatch.setenv("EMPATHY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("EMPATHY_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("EMPATHY_LOG_COLOR", "false")
    monkeypatch.setenv("EMPATHY_LOG_CONTEXT", "true")

    init_logging_from_env()

    assert LoggingConfig._configured is True
    assert LoggingConfig._level == logging.DEBUG
    assert LoggingConfig._log_dir == str(tmp_path)
    assert LoggingConfig._use_color is False
    assert LoggingConfig._include_context is True
