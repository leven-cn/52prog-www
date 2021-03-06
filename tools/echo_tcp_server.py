#!/usr/bin/env python

'''Echo TCP server.

Copyright 2015 Li Yun <leven.cn@gmail.com>.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import cookbook


class EchoRequestHandler(cookbook.RequestHandler):
    '''Echo server request handler.'''
    def handle(self, data):
        return data.encode()


server = None
try:
    server = cookbook.TCPServer((None, 8000), EchoRequestHandler,
                                logconf='default_log_conf.yaml')
    server.run()
finally:
    if server is not None:
        server.close()
