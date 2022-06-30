#!/usr/bin/env python3

import tornado.ioloop
from tornado.options import define, options, parse_command_line

from logger import get_logger
from app_server import DigiScriptServer

define('debug', type=bool, default=True, help='auto reload')
define('port', type=int, default=8080, help='port to listen on')


def main():
    tornado.options.parse_command_line()
    app = DigiScriptServer.instance(debug=options.debug)
    app.listen(options.port)
    get_logger().info(f'Listening on port: {options.port}')
    if options.debug:
        get_logger().warning('Running in debug mode')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
