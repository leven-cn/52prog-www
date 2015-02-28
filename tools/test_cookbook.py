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
import socketserver
import unittest
from unittest import mock

import cookbook


class GeneralTestCase(cookbook.GeneralTestCase):

    def setUp(self):
        super(GeneralTestCase, self).setUp()
        self.test_modules = ['cookbook.py']


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
@mock.patch('socketserver.BaseRequestHandler.handle', autospec=True)
@mock.patch('socket.socket', autospec=True)
class MockTCPServerTestCase(cookbook.MockServerTestCase):

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
class MockUDPServerTestCase(cookbook.MockServerTestCase):

    def mock_get_request(self, server_socket):
        '''Mock get_request() for UDP server.'''
        data = 'mock data'
        server_socket.recvfrom.return_value = (data,
                                               self.client_address)
        self.request = (data, server_socket)

    def test_server_succ(self, MockSocket, mock_handle):
        server = self.mock_server(MockSocket, mock_handle,
                                  socketserver.UDPServer)
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
