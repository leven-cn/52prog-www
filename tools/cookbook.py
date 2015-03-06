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
from abc import ABCMeta, abstractmethod
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
    '''A tiny TCP server, both IPv4 and IPv6 support.

    This class is built upon the `socket` and `select` modules.

    Instance Attributes:

        - socket: the socket object of server

    Simple Usage:

        class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self):
                data = self.readline()
                self.write(data)

        server = cookbook.TCPServer(('', 8000), MyTCPRequestHandler)
        server.run()

    '''

    _request_queue_size = 5

    def __init__(self, server_address, RequestHandlerClass, force_ipv4=False):
        self._RequestHandler = RequestHandlerClass

        if socket.has_ipv6 and not force_ipv4:
            self.socket = None
            host, port = server_address
            for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0,
                                          socket.AI_PASSIVE):
                family, type, proto, canonname, sockaddr = res
                try:
                    self.socket = socket.socket(family, type, proto)
                except OSError:
                    self.socket = None
                    continue

                # blocking mode for socket.makefile()
                self.socket.settimeout(None)

                # debug purpose
                if __debug__:
                    self.socket.setsockopt(socket.SOL_SOCKET,
                                           socket.SO_REUSEADDR, 1)

                try:
                    self.socket.bind(sockaddr)
                    self.socket.listen(self._request_queue_size)
                except OSError:
                    self.socket.close()
                    self.socket = None
                    continue
                break

            if self.socket is None:
                raise OSError

        else:  # IPv4 Only
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(None)  # blocking mode for socket.makefile()

            # debug purpose
            if __debug__:
                self.socket.setsockopt(socket.SOL_SOCKET,
                                       socket.SO_REUSEADDR, 1)

            self.socket.bind(server_address)
            self.socket.listen(self._request_queue_size)

    def close(self):
        '''Clean up the server.'''
        self.socket.close()

    def run(self, timeout=None):
        '''Run the server forever until SIGINT/KeyboardInterrupt occurred.

        @param timeout a time-out in seconds. When the timeout argument is
                       omitted the function blocks until at least one request
                       is ready.
        '''
        try:
            while True:
                self.handle_request(timeout)
        finally:
            self.close()

    def handle_request(self, timeout=None):
        '''Handle one request.

        @param timeout a time-out in seconds. When the timeout argument is
                       omitted the function blocks until at least one request
                       is ready.
        @exception OSError
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

        @exception OSError
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


class RequestHandler(metaclass=ABCMeta):
    '''The subclass of this class is instantiated for each request to be
    handled.

    Instance Attributes:

        - client_address: client address (Read-Only)
        - server: server instance (Read-Only)

    Subclasses MUST implement the handle() method.
    '''

    def __init__(self, request, client_address, server):
        self.client_address = client_address
        self.server = server

        # io.BufferedReader instance, default buffering.
        self._rfile = request.makefile('rb')

        # io.BufferedWriter instance, unbuffered.
        #
        # We make `_wfile` unbuffered because:
        # (a) often after a write() we want to read and we need to flush the
        #     line;
        # (b) big writes to unbuffered files are typically optimized by
        #     stdio even when big reads aren't.
        self._wfile = request.makefile('wb', 0)

        try:
            self.handle()
        finally:
            if not self._wfile.closed:
                try:
                    self._wfile.flush()
                except OSError:
                    pass
            self._wfile.close()
            self._rfile.close()

    @abstractmethod
    def handle(self):
        pass

    def readline(self):
        '''Read one line from client.

        @exception OSError
        @return data from client
        '''
        return self._rfile.readline()

    def read(self, size=-1):
        '''Read up to `size` bytes from client. If size omitted, read all the
        bytes from the stream until EOF.

        @param size bytes of data
        @exception OSError
        @return data from client
        '''
        return self._rfile.read(size)

    def write(self, data):
        '''Write data to client.

        @param data data to be written to client
        @exception OSError
        '''
        self._wfile.write(data)


class EchoRequestHandler(RequestHandler):
    '''Echo server request handler.'''
    def handle(self):
        data = self.readline()
        self.write(data)
