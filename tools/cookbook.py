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
import io
import errno
import socket
import select
import queue
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


def debug(msg):
    '''Print debugging message.

    @msg debugging message

    '''
    if __debug__:
        sys.stderr.write(msg)


def eintr_retry(func, *args):
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
            debug('Ignore EINTR')


class TCPServer(object):
    '''A tiny TCP server, both IPv4 and IPv6 support.

    This class is built upon the `socket` and `select` modules.

    Instance Attributes:

        - socket: the socket object of server, non-blocking mode
        - server_address: server's IP address in the form (host, port)
        - server_name: server's name

    Simple Usage:

        class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self, data):
                return data.encode()

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

                self.socket.settimeout(0.0)

                # make sense in testing environment
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
            self.socket.settimeout(0.0)

            # make sense in testing environment
            if __debug__:
                self.socket.setsockopt(socket.SOL_SOCKET,
                                       socket.SO_REUSEADDR, 1)

            self.socket.bind(server_address)
            self.socket.listen(self._request_queue_size)

        self.server_address = self.socket.getsockname()
        self.server_name = socket.getfqdn(self.server_address[0])

    def run(self, bufsize=io.DEFAULT_BUFFER_SIZE):
        '''Run the server forever until SIGINT/KeyboardInterrupt occurred.

        @param bufsize buffer size of reading from client
        '''
        inputs = [self.socket]
        outputs = []
        exceptional = []
        message_queues = {}
        handler = None

        try:
            while True:
                # Block until a request is ready.
                debug('Waiting for request...')
                rlist, wlist, xlist = eintr_retry(select.select,
                                                  inputs, outputs, inputs)

                # Read event
                for s in rlist:
                    if s is self.socket:
                        # A new request coming
                        request, client_address = s.accept()
                        debug('A request from {0}'.format(client_address))
                        if self.verify_request(request, client_address):
                            request.settimeout(0.0)
                            inputs.append(request)
                            message_queues[request] = queue.Queue()

                            handler = self._RequestHandler(client_address)
                    else:
                        # Read from client
                        address = s.getpeername()
                        try:
                            data = s.recv(bufsize)
                        except OSError as err:
                            debug('Error: reading from {0}: {1}'.format(
                                address, err))
                            continue
                        if data:
                            debug('Data from {0}: {1}'.format(address, data))
                            message_queues[s].put(data)
                            if s not in outputs:
                                outputs.append(s)
                        else:
                            debug('Closing {0}'.format(address))
                            inputs.remove(s)
                            if s in outputs:
                                outputs.remove(s)
                            self._close_request(s)
                            del message_queues[s]

                # Write event
                for s in wlist:
                    address = s.getpeername()
                    try:
                        next_data = message_queues[s].get_nowait()
                    except queue.Empty:
                        debug('Queue for {0} empty'.format(address))
                        outputs.remove(s)
                    else:
                        try:
                            data = handler.handle(next_data.decode())
                            debug('Sending {0} to {1}'.format(data, address))
                            s.sendall(data)
                        except:
                            self.handle_error(s)

                # Exception event
                for s in xlist:
                    debug('Exception condition on {0}'.format(s.getpeername()))
                    input.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    self._close_request(s)
                    del message_queues[s]
        finally:
            self.socket.close()

    def handle_error(self, request):
        '''Handle an error gracefully.

        @param request the client request
        @param client_address the client IP address in the form (host, port)

        May be override.
        '''
        pass

    def verify_request(self, request, client_address):
        '''Verify the request.

        @param request the client request
        @param client_address the client IP address in the form (host, port)

        May be override.
        '''
        return True

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

        - client_address: the client IP address in the form (host,port)

    Subclasses MUST implement the handle() method.
    '''

    def __init__(self, client_address):
        self.client_address = client_address

    @abstractmethod
    def handle(self, data):
        '''Return the handling result data.

        @param data input data ('utf-8')
        @return result (binary) data
        '''
        pass
