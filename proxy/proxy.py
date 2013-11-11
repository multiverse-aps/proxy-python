from __future__ import absolute_import

import time
import logging

from .compat import _urlparse, HTTPError
from .transport import HTTPTransport

logger = logging.getLogger('proxy')

class ClientState(object):
    ONLINE = 1
    ERROR = 0

    def __init__(self):
        self.status = self.ONLINE
        self.last_check = None
        self.retry_number = 0

    def should_try(self):
        if self.status == self.ONLINE:
            return True

        interval = min(self.retry_number, 6) ** 2

        if time.time() - self.last_check > interval:
            return True

        return False

    def set_fail(self):
        self.status = self.ERROR
        self.retry_number += 1
        self.last_check = time.time()

    def set_success(self):
        self.status = self.ONLINE
        self.last_check = None
        self.retry_number = 0

    def did_fail(self):
        return self.status == self.ERROR

class HTTPProxy(object):
    def __init__(self, uri, transport_cls=HTTPTransport, timeout=1.0):
        self.uri_base = uri
        self.timeout = timeout
        self._state = ClientState()

        self._configure_logging()
        cls = self.__class__
        self._logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))
        self._error_logger = logging.getLogger('proxy.errors')

        self._transport = transport_cls(timeout=self.timeout)

    def _configure_logging(self):
        logger = logging.getLogger('proxy')

        if logger.handlers:
            return

        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.INFO)

    def _successful_send(self):
        self._state.set_success()

    def _failed_send(self, e, url):
        if isinstance(e, HTTPError):
            body = e.read()
            self._error_logger.error(
            'Unable to reach proxy server: %s (url: %s, body: %s)',
            e, url, body, exc_info=True,
            extra={'data': {'body': body[:200], 'remote_url': url}})
        else:
            self._error_logger.error(
            'Unable to reach proxy server: %s (url: %s)', e, url,
            exc_info=True, extra={'data': {'remote_url': url}})

        self._error_logger.error('Failed to submit event: %s', url)
        self._state.set_fail()

    def send_remote(self, endpoint, method="GET", data=None, params=None, headers=None, success_cb=None, failure_cb=None):
        uri = _urlparse.urljoin(self.uri_base, endpoint)

        if not self._state.should_try():
            self._error_logger.error('Try later, client is inactive: %s', uri)
            return

        def _success_send(rv):
            self._successful_send()

            if success_cb:
                success_cb(rv)

        def _failed_send(e):
            self._failed_send(e, uri)

            if failure_cb:
                failure_cb()

        return self._transport.send(uri, method, data=data, headers=headers, success_cb=_success_send, failure_cb=_failed_send)

class RESTProxy(HTTPProxy):
    def __init__(self, uri, timeout=1.0):
        super(RESTProxy, self).__init__(uri, transport_cls=HTTPTransport, timeout=timeout)

    def create(self, data=None, params=None):
        rv = self.send_remote('', data=data, params=params)

        if not rv.status_code in (200, 201):
            self._error_logger.warn('CREATE returned status code {}.'.format(rv.status_code))

        return rv

    def update(self, resource_id, data=None, params=None):
        rv = self.send_remote('{}/'.format(resource_id), data=data, params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('UPDATE returned status code {}.'.format(rv.status_code))

        return rv

    def delete(self, resource_id, params=None):
        rv = self.send_remote('{}/'.format(resource_id), params=params)

        if not rv.status_code == 204:
            self._error_logger.warn('DELETE returned status code {}.'.format(rv.status_code))

        return rv

    def get(self, resource_id, params=None):
        rv = self.send_remote('{}/'.format(resource_id), params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('GET {} returned status code {}.'.format(rv.url, rv.rv.status_code))

        return rv

    def getmany(self, params=None):
        rv = self.send_remote('', "GET", params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('GET {} returned status code {}.'.format(rv.url, rv.status_code))

        return rv
