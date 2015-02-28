#!/usr/bin/env python

'''Python Cookbook.

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

import sys
import socket
import select
import socketserver
from unittest import mock
import unittest

import pep8


class GeneralTestCase(unittest.TestCase):
    '''General test case for module.

    Includes:

        - Python version
        - PEP 8 conformance (pep8 required)

    '''

    def setUp(self):
        '''Subclasses must provide `test_modules` and could configure it by
        override this method.'''
        self.test_modules = [__file__]
        self.pep8_quiet = False

    def test_py_version_conformance(self):
        self.assertGreaterEqual(sys.version_info, (3, 4),
                                'Python 3.4+ required')

    def test_pep8_conformance(self):
        pep8_style = pep8.StyleGuide(quiet=self.pep8_quiet)
        result = pep8_style.check_files(self.test_modules)
        self.assertEqual(result.total_errors, 0,
                         'Found {0} code style errors (and warnings)'
                         .format(result.total_errors))


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class MockServerTestCase(unittest.TestCase):

    def setUp(self):
        self.server_address = ('', 8000)
        self.client_address = ('client.host', 123456)
        self.fd = 1
        self.request_handler = socketserver.BaseRequestHandler
        self.request = self._mock_request()

    def mock_server(self, MockSocketClass, mock_handle, ServerClass,
                    timeout=None, mock_error=None):
        '''Mock a TCP socket server.'''
        server_socket = self._mock_socket(MockSocketClass, timeout)

        server = ServerClass(self.server_address, self.request_handler)
        if mock_error is not None:
            server.handle_error = mock.MagicMock(name='handle_error')

        self.assertEqual(server.address_family, socket.AF_INET)
        if ServerClass is socketserver.TCPServer:
            self.assertEqual(server.socket_type, socket.SOCK_STREAM)
        elif ServerClass is socketserver.UDPServer:
            self.assertEqual(server.socket_type, socket.SOCK_DGRAM)
        self.assertEqual(server.timeout, None)  # blocking mode by default
        self.assertEqual(server.RequestHandlerClass, self.request_handler)

        self.assertIs(server.socket, server_socket)
        self._mock_server_socket(server)
        self._mock_request_handler(mock_handle, mock_error)
        return server

    def mock_get_request(self, server_socket):
        '''Mock get_request().

        Must be override.
        '''
        pass

    def mock_server_activate(self, server):
        ''''Mock server_activate().

        May be override.
        '''
        pass

    def _mock_request(self):
        '''Mock a client request socket object.

        This instance has two methods: shutdown() and close().
        '''
        MockClientSocket = mock.MagicMock(name='ClientSocket')
        request = MockClientSocket.return_value

        return request

    def _mock_socket(self, MockSocketClass, timeout):
        '''Mock a server socket.'''
        server_socket = MockSocketClass.return_value
        server_socket.getsockname.return_value = self.server_address
        server_socket.fileno.return_value = self.fd
        server_socket.gettimeout.return_value = timeout
        if timeout is None:
            self.mock_get_request(server_socket)

        return server_socket

    def _mock_server_socket(self, server):
        '''Mock a server socket object.'''
        # Mock server.server_bind()
        server.socket.bind.assert_called_once_with(self.server_address)
        server.socket.getsockname.assert_called_once_with()
        self.assertEqual(server.server_address, self.server_address)

        # Mock server.server_activate()
        self.mock_server_activate(server)

    def _mock_request_handler(self, mock_handle, error):
        '''Mock RequestHandlerClass.'''
        mock_handle.side_effect = error

    def mock_handle_request(self, server, timeout=None, error=False):
        '''Mock handle_request().'''
        with mock.patch('select.select', autospec=True) as MockSelect:
            rlist = [server]
            if timeout is not None:
                rlist = []
            MockSelect.return_value = (rlist, [], [])

            server.handle_request()
            server.socket.gettimeout.assert_called_once_with()
            select.select.assert_called_once_with([server], [], [], timeout)

        if timeout is None:
            if server.socket_type == socket.SOCK_STREAM:
                server.socket.accept.assert_called_once_with()

            if error:
                server.handle_error.assert_called_once_with(
                    self.request,
                    self.client_address)

            if server.socket_type == socket.SOCK_STREAM:
                self.request.shutdown.assert_called_once_with(socket.SHUT_WR)
                self.request.close.assert_called_once_with()

    def mock_server_close(self, server):
        '''Mock server_close().'''
        server.server_close()
        server.socket.close.assert_called_once_with()


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
@mock.patch('socketserver.BaseRequestHandler.handle', autospec=True)
@mock.patch('socket.socket', autospec=True)
class MockTCPServerTestCase(MockServerTestCase):

    def mock_get_request(self, server_socket):
        '''Override for TCP server.'''
        server_socket.accept.return_value = (self.request, self.client_address)

    def mock_server_activate(self, server):
        '''Override for TCP server.'''
        server.socket.listen.assert_called_once_with(server.request_queue_size)

    def test_server_succ(self, MockSocket, mock_handle):
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.TCPServer)
        self.mock_handle_request(server)
        self.mock_server_close(server)

    def test_server_timeout(self, MockSocket, mock_handle):
        timeout = 0.5  # in seconds
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.TCPServer, timeout=timeout)
        self.mock_handle_request(server, timeout=timeout)
        self.mock_server_close(server)

    def test_server_error(self, MockSocket, mock_handle):
        error = KeyError
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.TCPServer, mock_error=error)
        self.mock_handle_request(server, error=True)
        self.mock_server_close(server)


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
@mock.patch('socketserver.BaseRequestHandler.handle', autospec=True)
@mock.patch('socket.socket', autospec=True)
class MockUDPServerTestCase(MockServerTestCase):

    def mock_get_request(self, server_socket):
        '''Mock get_request() for UDP server.'''
        data = 'mock data'
        server_socket.recvfrom.return_value = (data,
                                               self.client_address)
        self.request = (data, server_socket)

    def test_server_succ(self, MockSocket, mock_handle):
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.UDPServer)
        self.assertEqual(server.socket_type, socket.SOCK_DGRAM)
        self.mock_handle_request(server)
        self.mock_server_close(server)

    def test_server_timeout(self, MockSocket, mock_handle):
        timeout = 0.5  # in seconds
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.UDPServer, timeout=timeout)
        self.mock_handle_request(server, timeout=timeout)
        self.mock_server_close(server)

    def test_server_error(self, MockSocket, mock_handle):
        error = KeyError
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.UDPServer, mock_error=error)
        self.mock_handle_request(server, error=True)
        self.mock_server_close(server)


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
