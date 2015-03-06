#!/usr/bin/env python

'''Unit Testing for Python Cookbook.

Copyright (c) 2015 Li Yun <leven.cn@gmail.com>
All Rights Reserved.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

import sys
import socket
import select
import unittest
from unittest import mock

import cookbook


class GeneralTestCase(cookbook.GeneralTestCase):

    def setUp(self):
        super(GeneralTestCase, self).setUp()
        self.test_modules = [__file__, 'cookbook.py',
                             'echo_tcp_server.py', 'echo_tcp_client.py']


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class TCPServerTestCase(unittest.TestCase):

    # Mock a request handler.
    mock_handle = mock.MagicMock(name='handle')

    def setUp(self):
        self.server_address = (None, 8000)
        self.client_address = ('client.host', 123456)
        self.fd = 1

        # Mock a request.
        MockClientSocket = mock.MagicMock(name='ClientSocket')
        self.request = MockClientSocket.return_value
        self.request.makefile.return_value = None

        # Mock a server socket.
        self.socket_patcher = mock.patch('socket.socket', spec=True)
        MockSocket = self.socket_patcher.start()
        server_socket = MockSocket.return_value
        server_socket.fileno.return_value = self.fd
        server_socket.accept.return_value = (self.request, self.client_address)

        class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self):
                TCPServerTestCase.mock_handle()

        # Mock a server.
        self.servers = []
        for ServerClass in (cookbook.TCPServerV4,):
            server = ServerClass(self.server_address, MyTCPRequestHandler)
            server.socket.bind.assert_called_once_with(self.server_address)
            server.socket.listen.assert_called_once_with(mock.ANY)
            server.handle_timeout = mock.MagicMock(name='handle_timeout')
            server.handle_error = mock.MagicMock(name='handle_error')

            self.servers.append(server)

    def tearDown(self):
        for server in self.servers:
            server.close()
            server.socket.close.assert_called_once_with()
        self.socket_patcher.stop()

    def test_server_succ(self):
        for server in self.servers:
            self.mock_handle_request(server)
            self.assert_cleanup_request()

    def test_server_timeout(self):
        timeout = 0.5  # in seconds
        for server in self.servers:
            self.mock_handle_request(server, timeout)
            server.handle_timeout.assert_called_once_with()

    def test_server_error(self):
        error = KeyError
        for server in self.servers:
            self.mock_handle.side_effect = error
            self.mock_handle_request(server)
            server.handle_error.assert_called_once_with(self.request,
                                                        self.client_address)
            self.assert_cleanup_request()

    def mock_handle_request(self, server, timeout=None):
        '''Mock handle a request.'''
        with mock.patch('select.select', autospec=True) as MockSelect:
            if timeout is None:
                MockSelect.return_value = ([server.socket], [], [])
            else:
                MockSelect.return_value = ([], [], [])

            server.handle_request(timeout)
            select.select.assert_called_once_with([server.socket], [], [],
                                                  timeout)
            if timeout is None:
                server.socket.accept.assert_called_once_with()
                self.mock_handle.assert_called_with()

    def assert_cleanup_request(self):
        self.request.shutdown.assert_called_once_with(socket.SHUT_WR)
        self.request.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
