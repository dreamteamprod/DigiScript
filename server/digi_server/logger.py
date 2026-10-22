import logging
import sys
import threading
import weakref
from logging.handlers import RotatingFileHandler
from typing import Optional

from prometheus_client import Counter
from tornado.log import LogFormatter

from utils.log_buffer import (
    LogBufferHandler,
    get_client_buffer,
    get_server_buffer,
)


logger = logging.getLogger("DigiScript")
ALL_LOGGERS = [
    logging.getLogger("tornado.access"),
    logging.getLogger("tornado.application"),
    logging.getLogger("tornado.general"),
    # Stdlib/third-party loggers whose output would otherwise only reach stderr
    # (e.g. "Exception in callback ..." from fire-and-forget loop callbacks).
    logging.getLogger("asyncio"),
    logging.getLogger("alembic"),
    logging.getLogger("py.warnings"),
    logger,
]

UNHANDLED_ERRORS = Counter(
    "digiscript_unhandled_errors_total",
    "Unhandled exceptions caught by the global crash hooks",
    ["source"],
)
UNHANDLED_ERROR_SOURCES = ("sys_excepthook", "asyncio", "thread")
# Pre-register every label series at 0 so Prometheus increase() sees the very
# first error for each source.
for _source in UNHANDLED_ERROR_SOURCES:
    UNHANDLED_ERRORS.labels(source=_source)

# Guards install/uninstall; the state below is only touched while holding it.
_hooks_lock = threading.RLock()
# Previous hooks / warning state, saved at install; empty while not installed.
_saved_hooks: dict = {}
# Event loops we attached a handler to, mapped to the handler they had before.
_saved_loop_handlers: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _count_unhandled(source: str) -> None:
    UNHANDLED_ERRORS.labels(source=source).inc()


def _chain(previous, default, *args) -> None:
    """Call a pre-existing hook, skipping the interpreter default.

    The defaults only print to stderr, which would duplicate the log record.
    """
    if previous is None or previous is default:
        return
    try:
        previous(*args)
    except Exception:  # noqa: BLE001 - a broken foreign hook must not mask the crash
        logger.exception("Chained exception hook failed")


def _sys_excepthook(exc_type, exc_value, exc_tb):
    previous = _saved_hooks.get("sys")
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        (previous or sys.__excepthook__)(exc_type, exc_value, exc_tb)
        return
    _count_unhandled("sys_excepthook")
    try:
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    finally:
        _chain(previous, sys.__excepthook__, exc_type, exc_value, exc_tb)


def _threading_excepthook(args):
    previous = _saved_hooks.get("thread")
    if issubclass(args.exc_type, SystemExit):
        _chain(previous, threading.__excepthook__, args)
        return
    _count_unhandled("thread")
    try:
        thread_name = args.thread.name if args.thread else "<unknown>"
        logger.error(
            "Unhandled exception in thread %s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    finally:
        _chain(previous, threading.__excepthook__, args)


def _safe_repr(value) -> str:
    try:
        return repr(value)
    except Exception:  # noqa: BLE001 - arbitrary __repr__ must not break logging
        return f"<unrepresentable {type(value).__name__}>"


def _asyncio_exception_handler(loop, context):
    exc = context.get("exception")
    previous = _saved_loop_handlers.get(loop)
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        if previous is not None:
            previous(loop, context)
        else:
            loop.default_exception_handler(context)
        return
    try:
        message = context.get("message", "Unhandled exception in event loop")
        extras = "".join(
            f"\n{key}: {_safe_repr(context[key])}"
            for key in ("future", "task", "handle", "protocol", "transport")
            if key in context
        )
        if exc is None:
            # Message-only context (e.g. slow callback): a diagnostic, not a crash.
            logger.warning("%s%s", message, extras)
        else:
            _count_unhandled("asyncio")
            logger.error(
                "%s%s",
                message,
                extras,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
    except Exception:  # noqa: BLE001 - the handler itself must never raise
        try:
            loop.default_exception_handler(context)
        except Exception:  # noqa: BLE001, S110
            pass
    if previous is not None:
        _chain(previous, None, loop, context)


def install_exception_hooks(loop=None) -> None:
    """Route otherwise-invisible crashes into the DigiScript log.

    Installs ``sys.excepthook`` and ``threading.excepthook`` and the given
    loop's exception handler, and enables ``logging.captureWarnings`` so
    ``warnings.warn`` reaches the ``py.warnings`` logger. Each unhandled error
    increments ``digiscript_unhandled_errors_total{source}``. Pre-existing hooks
    are chained to after logging (interpreter defaults are skipped to avoid
    duplicate stderr output); ``KeyboardInterrupt`` and ``SystemExit`` keep
    their default behaviour. Idempotent and thread-safe.

    :param loop: Event loop to attach the exception handler to, or ``None`` to
        skip the loop handler.
    """
    with _hooks_lock:
        if not _saved_hooks:
            _saved_hooks["warnings"] = logging._warnings_showwarning is not None
            if sys.excepthook is not _sys_excepthook:
                _saved_hooks["sys"] = sys.excepthook
            else:
                _saved_hooks["sys"] = sys.__excepthook__
            if threading.excepthook is not _threading_excepthook:
                _saved_hooks["thread"] = threading.excepthook
            else:
                _saved_hooks["thread"] = threading.__excepthook__
            sys.excepthook = _sys_excepthook
            threading.excepthook = _threading_excepthook
            logging.captureWarnings(True)
        if loop is not None and loop not in _saved_loop_handlers:
            current = loop.get_exception_handler()
            if current is not _asyncio_exception_handler:
                _saved_loop_handlers[loop] = current
                loop.set_exception_handler(_asyncio_exception_handler)


def uninstall_exception_hooks() -> None:
    """Undo :func:`install_exception_hooks`.

    Restores ``sys.excepthook``, ``threading.excepthook``, the previous
    handler of every loop we attached to (unless closed) and the prior
    ``captureWarnings`` state. Idempotent and thread-safe.
    """
    with _hooks_lock:
        if not _saved_hooks:
            return
        # Only restore hooks that are still ours; never clobber a wrapper
        # installed after us.
        if sys.excepthook is _sys_excepthook:
            sys.excepthook = _saved_hooks["sys"]
        if threading.excepthook is _threading_excepthook:
            threading.excepthook = _saved_hooks["thread"]
        logging.captureWarnings(_saved_hooks["warnings"])
        for loop, previous in _saved_loop_handlers.items():
            if not loop.is_closed() and (
                loop.get_exception_handler() is _asyncio_exception_handler
            ):
                loop.set_exception_handler(previous)
        _saved_loop_handlers.clear()
        _saved_hooks.clear()


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


def configure_server_buffer(maxlen: int) -> LogBufferHandler:
    """Attach (or resize) the server log buffer to all server loggers.

    Idempotent: if the handler is already attached, only the buffer size is
    updated.

    :param maxlen: Maximum number of entries to keep in the buffer.
    :returns: The :class:`LogBufferHandler` singleton for server logs.
    """
    handler = get_server_buffer()
    handler.resize(maxlen)
    for _logger in ALL_LOGGERS:
        if handler not in _logger.handlers:
            _logger.addHandler(handler)
    return handler


def configure_client_buffer(maxlen: int) -> LogBufferHandler:
    """Attach (or resize) the client log buffer to the DigiScript.Client logger.

    Idempotent: if the handler is already attached, only the buffer size is
    updated.

    :param maxlen: Maximum number of entries to keep in the buffer.
    :returns: The :class:`LogBufferHandler` singleton for client logs.
    """
    handler = get_client_buffer()
    handler.resize(maxlen)
    client_logger = get_logger("Client")
    if handler not in client_logger.handlers:
        client_logger.addHandler(handler)
    return handler


def get_level_names_by_order():
    levels = logging.getLevelNamesMapping()
    sorted_levels = sorted(levels.items(), key=lambda x: x[1])
    return [name for name, _ in sorted_levels]
