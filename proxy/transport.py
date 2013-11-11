"""
track.transport
~~~~~~~~~~~~~~~

:copyright: (c) 2013 Simon Zimmermann.
:copyright: (c) 2010-2012 by the Sentry Team.
"""
from __future__ import absolute_import

import atexit
import logging
import os
import requests
import threading
import time

from .compat import Queue

DEFAULT_TIMEOUT = 10

logger = logging.getLogger('track.errors')

class AsyncWorker(object):
    _terminator = object()

    def __init__(self, shutdown_timeout=DEFAULT_TIMEOUT):
        self._queue = Queue(-1)
        self._lock = threading.Lock()
        self._thread = None
        self.options = {
            'shutdown_timeout': shutdown_timeout,
        }
        self.start()

    def main_thread_terminated(self):
        size = self._queue.qsize()
        if size:
            timeout = self.options['shutdown_timeout']
            print("Sentry is attempting to send %s pending error messages" % size)
            print("Waiting up to %s seconds" % timeout)
            if os.name == 'nt':
                print("Press Ctrl-Break to quit")
            else:
                print("Press Ctrl-C to quit")
            self.stop(timeout=timeout)

    def start(self):
        """
        Starts the task thread.
        """
        self._lock.acquire()
        try:
            if not self._thread:
                self._thread = threading.Thread(target=self._target)
                self._thread.setDaemon(True)
                self._thread.start()
        finally:
            self._lock.release()
            atexit.register(self.main_thread_terminated)

    def stop(self, timeout=None):
        """
        Stops the task thread. Synchronous!
        """
        self._lock.acquire()
        try:
            if self._thread:
                self._queue.put_nowait(self._terminator)
                self._thread.join(timeout=timeout)
                self._thread = None
        finally:
            self._lock.release()

    def queue(self, callback, *args, **kwargs):
        self._queue.put_nowait((callback, args, kwargs))

    def _target(self):
        while 1:
            record = self._queue.get()
            if record is self._terminator:
                break
            callback, args, kwargs = record
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.error('Failed processing job', exc_info=True)

            time.sleep(0)

class Response(object):
    def __init__(self, res):
        self._obj = res

    def __getattr__(self, attrib):
        return getattr(self._obj, attrib)

    def has_data(self):
        if not hasattr(self, '_has_data'):
            content_length = self.headers.get('Content-Length')

            if content_length:
                self._has_data = int(content_length) > 0
            else:
                self._has_data = len(self.text) > 0

        return self._has_data

    def data(self):
        if not self.has_data():
            return ''

        if 'application/json' in self.headers.get('Content-Type'):
            return self.json()

        return self.text

class HTTPTransport(object):
    async = False

    def __init__(self, timeout=None):
        self.timeout = timeout or 1.0

    def send_sync(self, url, method, data=None, params=None, headers=None, success_cb=None, failure_cb=None):
        try:
            rv = getattr(requests, method.lower())(url, params=params, data=data, headers=headers, timeout=self.timeout)
            res = Response(rv)
            res.raise_for_status()
            if success_cb:
                success_cb(res)
            return res
        except Exception as e:
            if failure_cb:
                failure_cb(e)

            raise e

    send = send_sync

class ThreadedHTTPTransport(HTTPTransport):
    async = True

    def get_worker(self):
        if not hasattr(self, '_worker'):
            self._worker = AsyncWorker()
        return self._worker

    def send(self, url, method, data=None, params=None, headers=None, success_cb=None, failure_cb=None):
        self.get_worker().queue(self.send_sync, url, method, data=data, params=params, headers=headers, success_cb=success_cb, failure_cb=failure_cb)