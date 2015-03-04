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
import errno
import socket
import select
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
        '''Subclasses must provide `test_modules` and could configure
        `pep8_quiet`.'''
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


def _eintr_retry(func, *args):
    ''''Restart a system call interrupted by `EINTR`.

    @param func the system call
    @return returned by the system call
    @exception OSError raised by the system call

    '''
    while True:
        try:
            return func(*args)
        except OSError as e:
            if e.errno != errno.EINTR:
                raise


class TCPServer(object):
    '''A tiny TCP server.

    This class is built upon the `socket` and `select` modules.

    Instance Attributes:

        - socket: the socket object of server

    '''

    _request_queue_size = 5

    def __init__(self, server_address, RequestHandler):
        self._RequestHandler = RequestHandler
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(0.0)  # non-blocking
        self.socket.bind(server_address)
        self.socket.listen(self._request_queue_size)

    def close(self):
        '''Clean up the server.'''
        self.socket.close()

    def handle_request(self, timeout=None):
        '''Handle one request.

        @param timeout a time-out in seconds. When the timeout argument is
                       omitted the function blocks until at least one request
                       is ready.
        @exception OSError raised by socket.accept()

        '''

        # Polling reduces our responsiveness to a
        # shutdown request and wastes CPU at all other times.
        assert timeout != 0.0, 'timeout=0.0 means a poll and never blocks!'
        rlist, wlist, xlist = _eintr_retry(select.select,
                                           [self.socket], [], [], timeout)
        if len(rlist) == 0:
            self.handle_timeout()
            return

        self._handle_request_noblock()

    def handle_timeout(self):
        '''Handle timeout.

        May be override.

        '''
        pass

    def handle_error(self, request, client_address):
        '''Handle an error gracefully.

        @param request the client request
        @param client_address the client address

        May be override.

        '''
        pass

    def verify_request(self, request, client_address):
        '''Verify the request.

        @param request the client request
        @param client_address the client address

        May be override.

        '''
        return True

    def _handle_request_noblock(self):
        '''Handle one request, without blocking.

        @exception OSError raised by socket.accept()

        '''
        request, client_address = self.socket.accept()
        if self.verify_request(request, client_address):
            try:
                self._process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self._close_request(request)

    def _process_request(self, request, client_address):
        '''Process one request after verification.

        @param request the client request
        @param client_address the client address

        '''
        self._RequestHandler(request, client_address, self)
        self._close_request(request)

    def _close_request(self, request):
        '''Clean up an individual request and shutdown it.

        @param request the client request

        '''
        try:
            # Explicitly shutdown.
            #
            # socket.close() merely releases
            # the socket and waits for GC to perform the actual close.
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass  # some platforms may raise ENOTCONN here
        request.close()
