#!/usr/bin/env python3
import asyncio
import logging
from tornado.options import define, options, parse_command_line

from digi_server.logger import get_logger, add_logging_level
from digi_server.app_server import DigiScriptServer

add_logging_level('TRACE', logging.DEBUG - 5)
get_logger().setLevel(logging.DEBUG)

define('debug', type=bool, default=True, help='auto reload')
define('port', type=int, default=8080, help='port to listen on')
define(
    'settings_path',
    type=str,
    default=None,
    help='Path to settings JSON file')


async def main():
    parse_command_line()

    app = DigiScriptServer(debug=options.debug,
                           settings_path=options.settings_path)
    await app.configure()

    app.listen(options.port)
    get_logger().info(f'Listening on port: {options.port}')
    if options.debug:
        get_logger().warning('Running in debug mode')
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
