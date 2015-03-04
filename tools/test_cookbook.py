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
        self.test_modules = [__file__, 'cookbook.py']


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class TCPServerTestCase(unittest.TestCase):

    def setUp(self):
        self.server_address = ('', 8000)
        self.client_address = ('client.host', 123456)
        self.fd = 1

        # Mock a request.
        MockClientSocket = mock.MagicMock(name='ClientSocket')
        self.request = MockClientSocket.return_value

        # Mock a server socket.
        self.socket_patcher = mock.patch('socket.socket', spec=True)
        MockSocket = self.socket_patcher.start()
        server_socket = MockSocket.return_value
        server_socket.getsockname.return_value = self.server_address
        server_socket.fileno.return_value = self.fd
        server_socket.accept.return_value = (self.request, self.client_address)

        # Mock a server.
        request_handler = mock.MagicMock(name='RequestHandler')
        self.server = cookbook.TCPServer(self.server_address, request_handler)
        self.server.socket.bind.assert_called_once_with(self.server_address)
        self.server.socket.listen.assert_called_once_with(mock.ANY)
        self.server.verify_request = mock.MagicMock(name='verify_request')
        self.server.verify_request.return_value = True
        self.server.handle_timeout = mock.MagicMock(name='handle_timeout')
        self.server.handle_error = mock.MagicMock(name='handle_error')

    def tearDown(self):
        self.server.close()
        self.server.socket.close.assert_called_once_with()
        self.socket_patcher.stop()

    def test_server_succ(self):
        self.mock_get_request()
        self.assert_cleanup_request()

    def test_server_timeout(self):
        timeout = 0.5  # in seconds
        self.mock_get_request(timeout)
        self.server.handle_timeout.assert_called_once_with()

    def test_server_error(self):
        error = KeyError
        self.server._RequestHandler.side_effect = error
        self.mock_get_request()
        self.server.handle_error.assert_called_once_with(self.request,
                                                         self.client_address)
        self.assert_cleanup_request()

    def mock_get_request(self, timeout=None):
        with mock.patch('select.select', autospec=True) as MockSelect:
            if timeout is None:
                MockSelect.return_value = ([self.server.socket], [], [])
            else:
                MockSelect.return_value = ([], [], [])

            self.server.handle_request(timeout)
            select.select.assert_called_once_with([self.server.socket], [], [],
                                                  timeout)
            if timeout is None:
                self.server.verify_request.assert_called_once_with(
                    self.request,
                    self.client_address)
                self.server.socket.accept.assert_called_once_with()

    def assert_cleanup_request(self):
        self.request.shutdown.assert_called_once_with(socket.SHUT_WR)
        self.request.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
