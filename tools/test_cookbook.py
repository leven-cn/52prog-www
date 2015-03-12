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
class SystemCallTestCase(unittest.TestCase):

    def test_eintr_retry_succ(self):
        for r in ('OK', None):
            mock_system_call = mock.MagicMock(name='sys_call', return_value=r)
            return_value = cookbook.eintr_retry(mock_system_call)
            mock_system_call.assert_called_with()
            self.assertEqual(return_value, r)
            return_value = cookbook.eintr_retry(mock_system_call, 'A')
            mock_system_call.assert_called_with('A')
            self.assertEqual(return_value, r)

    def test_eintr_retry_err(self):
        mock_system_call = mock.MagicMock(name='sys_call', side_effect=OSError)

        with self.assertRaises(OSError) as err:
            cookbook.eintr_retry(mock_system_call)
            mock_system_call.assert_called_with()

        with self.assertRaises(OSError) as err:
            cookbook.eintr_retry(mock_system_call, 'A')
            mock_system_call.assert_called_with('A')

    @unittest.skipIf(True, 'No good testing method for event-loop.')
    def test_eintr_retry_eintr(self):
        import errno
        err = OSError()
        err.errno = errno.EINTR

        mock_system_call = mock.MagicMock(name='sys_call', side_effect=err)


@unittest.skipIf(sys.version_info < (3, 3), 'unittest.mock since Python 3.3')
class TCPServerTestCase(unittest.TestCase):

    # Mock a request handler.
    mock_handle = mock.MagicMock(name='handle')

    class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self):
                TCPServerTestCase.mock_handle()

    def setUp(self):
        self.server_address = ('', 8000)
        self.client_address = ('client.host', 123456)

    def test_server_attributes_for_ipv4(self):
        s = cookbook.TCPServer(self.server_address, self.MyTCPRequestHandler,
                               force_ipv4=True)
        self.assertEqual(s.server_address, ('0.0.0.0', 8000))
        self.assertEqual(s.server_name, socket.gethostname())
        s.close()

    def test_server_attributes_for_ipv6(self):
        s = cookbook.TCPServer(self.server_address,
                               TCPServerTestCase.MyTCPRequestHandler)
        self.assertEqual(len(s.server_address), 4)
        self.assertIn(':', s.server_address[0])
        self.assertEqual(s.server_address[1], 8000)
        self.assertEqual(s.server_address[2], 0)
        self.assertEqual(s.server_name, socket.gethostname())
        s.close()


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
