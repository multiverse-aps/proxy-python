from __future__ import absolute_import

import time
import logging
import requests

from .compat import _urlparse
from .transport import HTTPTransport

logger = logging.getLogger('proxy')

class ProxyUnavailable(Exception):
    """
    Raised when the proxy server is unavailable.
    """

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

class closing(object):
    """Context to automatically close something at the end of a block.

    Code like this:

        with closing(<module>.open(<arguments>)) as f:
            <block>

    is equivalent to this:

        f = <module>.open(<arguments>)
        try:
            <block>
        finally:
            f.close()

    """
    def __init__(self, thing):
        self.thing = thing
    def __enter__(self):
        return self.thing
    def __exit__(self, *exc_info):
        if hasattr(self, 'close'):
            self.thing.close()

class HTTPProxy(object):
    def __init__(self, uri, transport_cls=HTTPTransport, timeout=1.0, max_retries=3, keep_alive=False):
        self.uri_base = uri
        self.timeout = timeout
        self._state = ClientState()

        self._configure_logging()
        cls = self.__class__
        self._logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))
        self._error_logger = logging.getLogger('proxy.errors')
        self._transport = transport_cls(keep_alive=keep_alive, timeout=self.timeout)

    def _configure_logging(self):
        logger = logging.getLogger('proxy')

        if logger.handlers:
            return

        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.INFO)

    def _successful_send(self):
        self._state.set_success()

    def _failed_send(self, e, url):
        if isinstance(e, requests.HTTPError):
            resp = e.response
            self._error_logger.error(
                'Unable to reach proxy server: %s (url: %s, body: %s)',
                e, url, resp.content, exc_info=True,
                extra={'data': {'body': resp.content[:200], 'remote_url': url}})
            if resp.status_code >= 500:
                self._state.set_fail()
        else:
            self._error_logger.error(
                'Unable to reach proxy server: %s (url: %s)', e, url,
                exc_info=True, extra={'data': {'remote_url': url}})
            self._state.set_fail()

        self._error_logger.error('Failed to submit event: %s', url)

    def send_closing(self, *args, **kwargs):
        return closing(self.send(*args, **kwargs))

    def send(self, endpoint, method="GET", data=None, json=None, params=None, headers=None, files=None, success_cb=None, failure_cb=None):
        uri = _urlparse.urljoin(self.uri_base, endpoint)

        if not self._state.should_try():
            self._error_logger.error('Try later, client is inactive: %s', uri)
            raise ProxyUnavailable()

        def _success_send(rv):
            self._error_logger.info('send {} {}ms'.format(uri, rv.elapsed.microseconds/1000.0))
            self._successful_send()

            if success_cb:
                success_cb(rv)

        def _failed_send(e):
            self._failed_send(e, uri)

            if failure_cb:
                failure_cb()

        return self._transport.send(uri, method, data=data, json=json, params=params, headers=headers, files=None, success_cb=_success_send, failure_cb=_failed_send)

class RESTProxy(HTTPProxy):
    def __init__(self, uri, timeout=1.0, keep_alive=False):
        super(RESTProxy, self).__init__(uri, transport_cls=HTTPTransport, timeout=timeout, keep_alive=keep_alive)

    def create(self, method="POST", data=None, params=None):
        rv = self.send('', method=method, data=data, params=params)

        if not rv.status_code in (200, 201):
            self._error_logger.warn('CREATE returned status code {}.'.format(rv.status_code))

        return rv

    def update(self, resource_id, method="PUT", data=None, params=None):
        rv = self.send('{}/'.format(resource_id), method=method, data=data, params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('UPDATE returned status code {}.'.format(rv.status_code))

        return rv

    def delete(self, resource_id, method="DELETE", params=None):
        rv = self.send('{}/'.format(resource_id), method=method, params=params)

        if not rv.status_code == 204:
            self._error_logger.warn('DELETE returned status code {}.'.format(rv.status_code))

        return rv

    def get(self, resource_id, method="GET", params=None):
        rv = self.send('{}/'.format(resource_id), method=method, params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('GET {} returned status code {}.'.format(rv.url, rv.rv.status_code))

        return rv

    def getmany(self, method="GET", params=None):
        rv = self.send('', method=method, params=params)

        if not rv.status_code == 200:
            self._error_logger.warn('GET {} returned status code {}.'.format(rv.url, rv.status_code))

        return rv
