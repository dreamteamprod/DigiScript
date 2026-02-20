import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from tornado.log import LogFormatter


logger = logging.getLogger("DigiScript")
ALL_LOGGERS = [
    logging.getLogger("tornado.access"),
    logging.getLogger("tornado.application"),
    logging.getLogger("tornado.general"),
    logger,
]


def get_logger(name: Optional[str] = None):
    if name:
        return logger.getChild(name)
    return logger


def configure_log_level(log_level=logging.DEBUG):
    for _logger in ALL_LOGGERS:
        logger.info(f"Setting log level to {log_level} for logger: {_logger.name}")
        _logger.setLevel(log_level)


def configure_file_logging(
    log_path,
    max_size_mb=100,
    log_backups=5,
    handler=None,
):
    size_bytes = max_size_mb * 1024 * 1024

    if handler:
        for _logger in ALL_LOGGERS:
            _logger.removeHandler(handler)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=size_bytes, backupCount=log_backups
    )
    file_handler.setFormatter(LogFormatter(color=False))
    for _logger in ALL_LOGGERS:
        _logger.addHandler(file_handler)
    return file_handler


def configure_db_logging(
    log_level=logging.DEBUG,
    log_path=None,
    max_size_mb=100,
    log_backups=5,
    handler=None,
    enable_db_logging=False,
):
    size_bytes = max_size_mb * 1024 * 1024
    db_logger = logging.getLogger("sqlalchemy.engine")

    if handler:
        db_logger.removeHandler(handler)

    if not enable_db_logging:
        logger.info(f"Disabling logger: {db_logger.name}")
        return None

    logger.info(f"Setting log level to {log_level} for logger: {db_logger.name}")
    db_logger.setLevel(log_level)
    file_handler = None
    if log_path:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=size_bytes, backupCount=log_backups
        )
        file_handler.setFormatter(LogFormatter(color=False))
        db_logger.addHandler(file_handler)
        db_logger.propagate = False
    return file_handler


CLIENT_LEVEL_MAP = {
    "TRACE": 5,  # Registered via add_logging_level("TRACE", logging.DEBUG - 5) in main.py
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,  # loglevel npm uses WARN; Python uses WARNING
    "ERROR": logging.ERROR,
    "SILENT": logging.CRITICAL + 1,  # No Python equivalent; suppress all
}


def map_client_level(level_name: str) -> int:
    """Map a loglevel npm level name to a Python logging integer.

    :param level_name: Level name from the loglevel npm package (e.g. TRACE, WARN).
    :returns: The corresponding Python logging integer level.
    """
    return CLIENT_LEVEL_MAP.get(level_name.upper(), logging.INFO)


def configure_client_logging(
    log_path,
    max_size_mb=100,
    log_backups=5,
    handler=None,
    log_level=logging.DEBUG,
):
    size_bytes = max_size_mb * 1024 * 1024
    client_logger = get_logger("Client")

    if handler:
        client_logger.removeHandler(handler)

    if isinstance(log_level, str):
        log_level = map_client_level(log_level)

    client_logger.setLevel(log_level)
    file_handler = None
    if log_path:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=size_bytes, backupCount=log_backups
        )
        file_handler.setFormatter(LogFormatter(color=False))
        client_logger.addHandler(file_handler)
        # Prevent propagation to avoid polluting the server console
        client_logger.propagate = False
    return file_handler


def add_logging_level(level_name, level_num, method_name=None):
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError(f"{level_name} already defined in logging module")
    if hasattr(logging, method_name):
        raise AttributeError(f"{method_name} already defined in logging module")
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f"{method_name} already defined in logger class")

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


def get_level_names_by_order():
    levels = logging.getLevelNamesMapping()
    sorted_levels = sorted(levels.items(), key=lambda x: x[1])
    return [name for name, _ in sorted_levels]
