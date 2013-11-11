import proxy
import time
import unittest
from proxy.proxy import ClientState
from proxy.compat import _urlparse

class ClientStateTest(unittest.TestCase):
    def test_should_try_online(self):
        state = ClientState()
        self.assertEquals(state.should_try(), True)

    def test_should_try_new_error(self):
        state = ClientState()
        state.status = state.ERROR
        state.last_check = time.time()
        state.retry_number = 1
        self.assertEquals(state.should_try(), False)

    def test_should_try_time_passed_error(self):
        state = ClientState()
        state.status = state.ERROR
        state.last_check = time.time() - 10
        state.retry_number = 1
        self.assertEquals(state.should_try(), True)

    def test_set_fail(self):
        state = ClientState()
        state.set_fail()
        self.assertEquals(state.status, state.ERROR)
        self.assertNotEquals(state.last_check, None)
        self.assertEquals(state.retry_number, 1)

    def test_set_success(self):
        state = ClientState()
        state.status = state.ERROR
        state.last_check = 'foo'
        state.retry_number = 0
        state.set_success()
        self.assertEquals(state.status, state.ONLINE)
        self.assertEquals(state.last_check, None)
        self.assertEquals(state.retry_number, 0)

class TrackTestCase(unittest.TestCase):
    pass
    #def test_http_proxy(self):
    #    uri = _urlparse.urljoin('http://localhost:6063/shop/v1/', 'product/')
    #    h = proxy.RESTProxy(uri)
    #    for x in range(10):
    #        rv = h.getmany(params={'profile_id': 1})
    #        print '{}ms'.format(rv.elapsed.microseconds/1000.0)
