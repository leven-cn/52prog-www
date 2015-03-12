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
import os
import io
import errno
import logging
import logging.config
import socket
import select
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

    This class is built upon the `socket` and `select` modules.

    Instance Attributes:

        - server_address: server's IP address in the form (host, port)
        - server_name: server's name

    Simple Usage:

        class MyTCPRequestHandler(cookbook.RequestHandler):
            def handle(self, data):
                return data.encode()

        try:
            server = cookbook.TCPServer(('', 8000), MyTCPRequestHandler)
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

    def __init__(self, server_address, RequestHandlerClass,
                 logconf=None, force_ipv4=False):
        self._RequestHandler = RequestHandlerClass

        if socket.has_ipv6 and not force_ipv4:
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

        else:  # IPv4 Only
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

        # Set logging system
        #
        # Optimization:
        #
        #     if logger.isEnabledFor(logging.DEBUG):
        #         logger.debug('Message with %s, %s', expensive_func1(),
        #                      expensive_func2())
        #
        class_name = self.__class__.__name__
        if os.name == 'posix':
            logfile_error_handler_class = 'logging.handler.WatchedFileHandler'
        elif os.name == 'nt':
            logfile_error_handler_class = 'logging.FileHandler'
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
                    'class': logfile_error_handler_class,
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
        inputs = [self._socket]
        outputs = []
        exceptional = []
        message_queues = {}
        handler = None

        self.log_info('Hosting on {0} ...'.format(self.server_name))
        while True:
            # Block until a request is ready.
            self.log_debug('Waiting for request ...')
            rlist, wlist, xlist = eintr_retry(select.select,
                                              inputs, outputs, inputs)

            # Read event
            for s in rlist:
                if s is self._socket:
                    # A new request coming
                    request, client_addr = s.accept()
                    self.log_info('A request from {0}'.format(client_addr))
                    if self.verify_request(request, client_addr):
                        request.settimeout(0.0)
                        inputs.append(request)
                        message_queues[request] = queue.Queue()

                        handler = self._RequestHandler(client_addr)
                else:
                    # Read from client
                    address = s.getpeername()
                    try:
                        data = s.recv(bufsize)
                    except OSError as err:
                        self.log_error('Reading from {0}: {1}'.format(
                            address, err))
                        continue
                    if data:
                        self.log_debug('Data from {0}: {1}'.format(
                            address, data))
                        message_queues[s].put(data)
                        if s not in outputs:
                            outputs.append(s)
                    else:
                        self.log_info('Closing {0}'.format(address))
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
                    self.log_debug('Queue for {0} empty'.format(address))
                    outputs.remove(s)
                else:
                    try:
                        data = handler.handle(next_data.decode())
                        self.log_debug('Sending {0} to {1}'.format(
                            data, address))
                        s.sendall(data)
                    except:
                        self.handle_error(s)

            # Exception event
            for s in xlist:
                self.log_warning('Exception condition on {0}'.format(
                    s.getpeername()))
                input.remove(s)
                if s in outputs:
                    outputs.remove(s)
                self._close_request(s)
                del message_queues[s]

    def close(self):
        '''Clean up server.'''
        if self._socket is not None:
            self._socket.close()

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
