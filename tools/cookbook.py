#!/usr/bin/env python

'''Python Cookbook.

Requirements
======

Third Party Packages:

  - pep8
  - pyyaml

Packages listed above could be installed by (root required):

    pip3 install --upgrade pip
    pip3 install --upgrade pep8 pyyaml

======
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


Acknowledge
======

PyYAML is written by Kirill Simonov <xi@resolvent.net>.  It is released
under the MIT license.

'''

import sys
from abc import ABCMeta, abstractmethod
import io
import errno
import logging
import logging.config
import socket
import selectors
import queue
from unittest import mock
import unittest

import pep8
import yaml


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


class TCPServer(object):
    '''A tiny TCP server, both IPv4 and IPv6 support.

    This class is built upon the `socket` and `selectors` modules.

    Instance Attributes:

        - server_address: server's IP address in the form (host, port)
        - server_name: server's name

    Simple Usage:

        class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self, data):
                return data.encode()

        try:
            server = cookbook.TCPServer(('0.0.0.0', 8000), MyTCPRequestHandler)
            server.run()
        except OSError:
            pass
        finally:
            server.close()

    Logging Levels:

        The numeric values of logging levels are given in the following table.
        These are primarily of interest if you want to define your own levels,
        and need them to have specific values relative to the predefined
        levels. If you define a level with the same numeric value, it
        overwrites the predefined value; the predefined name is lost.

        Level      | Numeric value
        =======================
        CRITICAL   | 50
        ERROR      | 40
        WARNING    | 30
        INFO       | 20
        DEBUG      | 10
        NOTSET     | 0

    '''

    _request_queue_size = 5

    def __init__(self, server_address, RequestHandlerClass, logconf=None):

        import os
        if os.name != 'posix':
            raise ValueError('NOT conformance to POSIX!')

        self._RequestHandler = RequestHandlerClass

        if socket.has_ipv6:
            self._socket = None
            host, port = server_address
            for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0,
                                          socket.AI_PASSIVE):
                family, type, proto, canonname, sockaddr = res
                try:
                    self._socket = socket.socket(family, type, proto)
                except OSError:
                    self._socket = None
                    continue

                self._socket.settimeout(0.0)

                # make sense in testing environment
                if __debug__:
                    self._socket.setsockopt(socket.SOL_SOCKET,
                                            socket.SO_REUSEADDR, 1)

                try:
                    self._socket.bind(sockaddr)
                    self._socket.listen(self._request_queue_size)
                except OSError:
                    self._socket.close()
                    self._socket = None
                    continue
                break

            if self._socket is None:
                raise OSError

        else:  # for OS not support for IPv6
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(0.0)

            # make sense in testing environment
            if __debug__:
                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR, 1)

            self._socket.bind(server_address)
            self._socket.listen(self._request_queue_size)

        self.server_address = self._socket.getsockname()
        self.server_name = socket.getfqdn(self.server_address[0])

        self._message_queues = {}
        self._handler = None

        # Set logging system
        #
        # Optimization:
        #
        #     if logger.isEnabledFor(logging.DEBUG):
        #         logger.debug('Message with %s, %s', expensive_func1(),
        #                      expensive_func2())
        #
        class_name = self.__class__.__name__
        default_log_conf = {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(levelname)s] %(asctime)s %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'default',
                    'stream': 'ext://sys.stderr'
                },
                'logfile': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'filename': '{0}.log'.format(class_name),
                    'mode': 'a',
                    'maxBytes': 1048576,  # 10M
                    'backupCount': 5,
                    'encoding': 'utf-8',
                    'formatter': 'default'
                },
                'logfile-error': {
                    'class': 'logging.handlers.WatchedFileHandler',
                    'level': 'ERROR',
                    'filename': '{0}-error.log'.format(class_name),
                    'mode': 'w',
                    'encoding': 'utf-8',
                    'formatter': 'default'
                }
            },
            'loggers': {
                class_name: {
                    'level': 'DEBUG',
                    'handlers': ['console', 'logfile', 'logfile-error'],
                    'propagate': False
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['console']
            }
        }
        if logconf is None:
            logging.config.dictConfig(default_log_conf)
        else:
            with open(logconf, 'r') as f:
                logging.config.dictConfig(yaml.load(f))
        self._logger = logging.getLogger(self.__class__.__name__)

        self.log_info('Hosting on {0} ({1})...'.format(
            self.server_name, self.server_address))

    @staticmethod
    def debug(msg):
        '''Print debugging messages to the console.

        @param msg debugging message

        '''
        if __debug__:
            sys.stderr.write(msg)

    def log_debug(self, msg):
        '''Log a debug-level message.

        @param msg debug-level message

        '''
        self._logger.debug(msg)

    def log_info(self, msg):
        '''Log a info-level message.

        @param msg info-level message

        '''
        self._logger.info(msg)

    def log_error(self, msg):
        '''Log a error-level message.

        @param msg error-level message

        '''
        self._logger.error(msg)

    def log_warning(self, msg):
        '''Log a warning-level message.

        @param msg warning-level message

        '''
        self._logger.warning(msg)

    def run(self, bufsize=io.DEFAULT_BUFFER_SIZE):
        '''Run the server forever until SIGINT/KeyboardInterrupt occurred.

        @param bufsize buffer size of reading from client
        '''
        EV_ACCEPT = 0  # Identify a new request coming

        with selectors.DefaultSelector() as io_selector:
            io_selector.register(self._socket, selectors.EVENT_READ, EV_ACCEPT)

            while True:
                # Block until a request is ready.
                self.log_debug('Waiting for request ...')
                e = io_selector.select()

                for key, events in e:
                    if key.data == EV_ACCEPT:
                        self._accept(io_selector)

                    elif events & selectors.EVENT_READ:
                        try:
                            self._read(key.fileobj, bufsize, io_selector)
                        except OSError:
                            pass

                    elif events & selectors.EVENT_WRITE:
                        self._write(key.fileobj, io_selector)

    def close(self):
        '''Clean up server.'''
        if self._socket is not None:
            self._socket.close()

    def verify_request(self, request, client_address):
        '''Verify the request.

        @param request the client request
        @param client_address the client IP address in the form (host, port)

        May be override.
        '''
        return True

    def _accept(self, io_selector):
        '''A new request coming.

        @param io_selector I/O multiplex mechanism used
        '''
        request, client_addr = self._socket.accept()
        self.log_info('A request from {0}'.format(client_addr))

        if self.verify_request(request, client_addr):
            request.settimeout(0.0)
            io_selector.register(request, selectors.EVENT_READ)
            self._message_queues[request] = queue.Queue()

            self._handler = self._RequestHandler(request)

    def _read(self, request, bufsize, io_selector):
        '''Read data from client.

        @param request request (socket) object ready for read
        @param bufsize buffer size of reading from client
        @param io_selector I/O multiplex mechanism used
        @exception OSError
        '''
        address = request.getpeername()
        try:
            data = request.recv(bufsize)
        except OSError as err:
            self.log_error('Reading from {0}: {1}'.format(address, err))
            raise
        if data:
            self.log_debug('Reading from {0}: {1}'.format(address, data))
            self._message_queues[request].put(data)
            io_selector.modify(request, selectors.EVENT_WRITE)
        else:
            self.log_info('Closing {0}'.format(address))
            self._cleanup_request(request, io_selector)

    def _write(self, request, io_selector):
        '''Write data to client.

        @param request request (socket) object ready for writing
        @param io_selector I/O multiplex mechanism used
        '''
        address = request.getpeername()
        try:
            next_data = self._message_queues[request].get_nowait()
        except queue.Empty:
            self.log_debug('Queue for {0} empty'.format(address))
        else:
            try:
                data = self._handler.handle(next_data.decode())
                self.log_debug('Sending to {0}: {1}'.format(address, data))
                request.sendall(data)
                io_selector.modify(request, selectors.EVENT_READ)
            except:
                self._handler.handle_error()
                self._cleanup_request(request, io_selector)

    def _cleanup_request(self, request, io_selector):
        '''Clean up an individual request.

        @param request the client request
        @param io_selector I/O multiplex mechanism used
        '''
        io_selector.unregister(request)
        self._close_request(request)
        del self._message_queues[request]

    def _close_request(self, request):
        '''Close an individual request.

        @param request the client request
        '''
        try:
            # Explicitly shutdown
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

        - request: the client request

    Subclasses MUST implement the handle() method.
    '''

    def __init__(self, request):
        self.request = request

    @abstractmethod
    def handle(self, data):
        '''Return the handling result data.

        @param data input data ('utf-8')
        @return result (binary) data
        '''
        pass

    def handle_error(self):
        '''Handle an error gracefully.

        May be override.
        '''
        sys.stderr.write('error')
