#!/usr/bin/env python

'''Echo TCP client.

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

import socket


client = None
try:
    client = socket.create_connection(('localhost', 8000), 3.0)
    while True:
        data = input('Send data, [Q] for quit: ')
        if data == 'Q':
            break

        data += '\n'
        client.sendall(data.encode())
        data = client.recv(1024)
        print('from server: ', data)
finally:
    if client is not None:
        client.close()
