#!/usr/bin/env python3

import logging
import tornado.ioloop
from tornado.options import define, options

from utils.logger import get_logger, add_logging_level
from app_server import DigiScriptServer

add_logging_level('TRACE', logging.DEBUG - 5)
get_logger().setLevel(logging.DEBUG)

define('debug', type=bool, default=True, help='auto reload')
define('port', type=int, default=8080, help='port to listen on')
define(
    'settings_path',
    type=str,
    default=None,
    help='Path to settings JSON file')


def main():
    tornado.options.parse_command_line()
    app = DigiScriptServer(debug=options.debug,
                           settings_path=options.settings_path)
    app.listen(options.port)
    get_logger().info(f'Listening on port: {options.port}')
    if options.debug:
        get_logger().warning('Running in debug mode')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
