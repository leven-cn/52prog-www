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
import socket
import unittest
try:
    from unittest.mock import patch
except ImportError:
    pass

import pep8


class GeneralTestCase(unittest.TestCase):
    '''General test case for module.

    Includes:

        - Python version
        - PEP 8 conformance

    '''

    def setUp(self):
        '''Subclasses must provide `test_modules` and could configure it by
        override this method.'''
        self.test_modules = [__file__]
        self.pep8_quiet = False

    def test_py_version_conformance(self):
        # Python 2.7.9+ or 3.4+ required
        if sys.version_info.major == 2:
            self.assertEqual(sys.version_info.minor, 7,
                             'Python 2.7.9+ required')
            self.assertGreaterEqual(sys.version_info.micro, 9,
                                    'Python 2.7.9+ required')
        elif sys.version_info.major == 3:
            self.assertGreaterEqual(sys.version_info.minor, 4,
                                    'Python 3.4+ required')

    def test_pep8_conformance(self):
        pep8_style = pep8.StyleGuide(quiet=self.pep8_quiet)
        result = pep8_style.check_files(self.test_modules)
        self.assertEqual(result.total_errors, 0,
                         'Found {0} code style errors (and warnings)'
                         .format(result.total_errors))


@unittest.skipUnless(sys.version_info > (3, 3),
                     'unittest.mock module support, Python 3.3+ required')
class SocketTestCase(unittest.TestCase):
    '''Test case for BSD socket APIs.

    Includes:

        - TCP
        - UDP

    '''

    def setUp(self):
        self.patcher = patch('socket.socket', autospec=True)
        self.MockSocket = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_mocksocket(self):
        self.assertIs(self.MockSocket, socket.socket)

        sock = self.MockSocket(socket.AF_INET, socket.SOCK_STREAM)
        socket.socket.assert_called_once_with(socket.AF_INET,
                                              socket.SOCK_STREAM)
        sock.close()
        sock.close.assert_called_once_with()

    def tcp_socket_handle(self):
        pass

    def test_tcp_socket(self):
        with self.MockSocket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            self.tcp_socket_handle()

    def udp_socket_handle(self):
        pass

    def test_udp_socket(self):
        with self.MockSocket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            self.udp_socket_handle()


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
