#!/usr/bin/env python3

import logging
import tornado.ioloop
from tornado.options import define, options, parse_command_line

from server import DigiScriptServer

log = logging.getLogger(__name__)

define('debug', type=bool, default=True, help='auto reload')
define('port', type=int, default=8080, help='port to listen on')


def main():
    tornado.options.parse_command_line()
    app = DigiScriptServer(debug=options.debug)
    app.listen(options.port)
    log.info(f'Listening on port: {options.port}')
    if options.debug:
        log.warning('Running in debug mode')
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
