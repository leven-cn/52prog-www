#!/usr/bin/env python

'''Python Cookbook.

Copyright 2015 Li Yun.

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
import socketserver
import unittest
try:
    from unittest.mock import patch, MagicMock
except ImportError:
    pass

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
class MockSocketServerTestCase(unittest.TestCase):

    def setUp(self):
        self.host = ''
        self.port = 8000
        self.server_address = (self.host, self.port)

    def create_server(self):
        '''Subclasses must return a socket server.'''
        mock_server = MagicMock(name='mock_server')
        mock_server.server_address = self.server_address
        return mock_server

    def test_server(self):
        mock_server = self.create_server()
        self.assertEqual(mock_server.server_address, self.server_address)
        # self.assertEqual(srv.RequestHandlerClass, None)


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class MockTCPServerTestCase(MockSocketServerTestCase):

    def setUp(self):
        super(MockTCPServerTestCase, self).setUp()

    @patch('socketserver.TCPServer', autospec=True)
    def create_server(self, MockTCPServer):
        mock_server = MockTCPServer.return_value
        mock_server.server_address = self.server_address
        return mock_server


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class MockUDPServerTestCase(MockSocketServerTestCase):

    def setUp(self):
        super(MockUDPServerTestCase, self).setUp()

    @patch('socketserver.UDPServer', autospec=True)
    def create_server(self, MockUDPServer):
        mock_server = MockUDPServer.return_value
        mock_server.server_address = self.server_address
        return mock_server


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
