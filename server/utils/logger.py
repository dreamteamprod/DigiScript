import logging
from logging.handlers import RotatingFileHandler


from tornado.log import LogFormatter

logger = logging.getLogger('DigiScript')


def get_logger():
    return logger


def configure_file_logging(log_path, max_size_mb=100, log_backups=5):
    size_bytes = max_size_mb*1024*1024
    file_handler = RotatingFileHandler(log_path,
                                       maxBytes=size_bytes,
                                       backupCount=log_backups)
    file_handler.setFormatter(LogFormatter(color=False))
    get_logger().addHandler(file_handler)
    logging.getLogger('tornado.access').addHandler(file_handler)
    logging.getLogger('tornado.application').addHandler(file_handler)
    logging.getLogger('tornado.general').addHandler(file_handler)


def configure_db_logging(log_level=logging.DEBUG, log_path=None, max_size_mb=100, log_backups=5):
    size_bytes = max_size_mb*1024*1024
    db_logger = logging.getLogger('sqlalchemy.engine')
    db_logger.setLevel(log_level)
    if log_path:
        file_handler = RotatingFileHandler(log_path,
                                           maxBytes=size_bytes,
                                           backupCount=log_backups)
        file_handler.setFormatter(LogFormatter(color=False))
        db_logger.addHandler(file_handler)
        db_logger.propagate = False


def add_logging_level(level_name, level_num, method_name=None):
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError(
            '{} already defined in logging module'.format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError(
            '{} already defined in logging module'.format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(
            '{} already defined in logger class'.format(method_name))

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)
