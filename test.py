import unittest
import sys
from time import sleep

try:
    import dev_appserver
except ImportError:
    raise ImportError('App Engine must be in PYTHONPATH.')
    sys.exit()

dev_appserver.fix_sys_path()

from google.appengine.api import memcache
from google.appengine.ext import testbed, webapp
from google.appengine.datastore import datastore_stub_util

import __init__ as gae_html

UCHAR = u"\u03B4" # lowercase delta


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
    
    def tearDown(self):
        self.testbed.deactivate()


class MockController(webapp.RequestHandler):

    PATH = "/test-path"
    HTML = "<html>    <body>test response<!-- with comment -->" + UCHAR + "    </body></html>"
    MINIFIED = "<html> <body>test response" + UCHAR + " </body></html>"
    MINIFIED_COMMENT = "<html> <body>test response<!-- with comment -->" + UCHAR + " </body></html>"

    def __init__(self):
        super(MockController, self).__init__()
        self.called = False

    def get(self):
        self.response.write(self.HTML)
        self.called = True


class BaseTestController(BaseTestCase):
    """ abstract base class for tests that need request and response mocking """

    def setUp(self):
        super(BaseTestController, self).setUp()

        self.controller = MockController()
        self.controller.initialize(self.getMockRequest(), self.getMockResponse())

    def getMockRequest(self):
        class MockRequest(webapp.Request):
            path = url = MockController.PATH
        return MockRequest({})

    def getMockResponse(self):
        class MockResponse(webapp.Response):
            unicode_body = ""
            def write(self, content):
                self.unicode_body = content
        return MockResponse()


class TestDecorator(BaseTestController):

    def test_default(self):
        decorator = gae_html.cacheAndRender()(MockController.get)

        response = decorator(self.controller)
        assert response == MockController.MINIFIED
        assert self.controller.called

        # should be in memcache but not datastore by default
        from_memcache = memcache.get(MockController.PATH)
        assert from_memcache == MockController.MINIFIED

        from_datastore = gae_html.HTMLCache.get_by_id(MockController.PATH, use_memcache=False)
        assert from_datastore is None

    def test_expires(self):
        # we also use the datastore here so that we can check the expires on that
        decorator = gae_html.cacheAndRender(expires=1, use_datastore=True)(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.MINIFIED
        assert self.controller.called

        from_memcache = memcache.get(MockController.PATH)
        assert from_memcache == MockController.MINIFIED

        from_datastore = gae_html.HTMLCache.get_by_id(MockController.PATH, use_memcache=False)
        assert from_datastore is not None
        assert from_datastore.expires == 1

        # sleep and then check the cache again
        sleep(1)

        from_memcache = memcache.get(MockController.PATH)
        assert from_memcache is None

    def test_minify(self):
        decorator = gae_html.cacheAndRender(minify=False)(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.HTML
        assert self.controller.called

    def test_include_comments(self):
        decorator = gae_html.cacheAndRender(include_comments=True)(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.MINIFIED_COMMENT
        assert self.controller.called

    def test_use_datastore(self):
        decorator = gae_html.cacheAndRender(use_datastore=True)(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.MINIFIED
        assert self.controller.called

        from_datastore = gae_html.HTMLCache.get_by_id(MockController.PATH, use_memcache=False)
        assert from_datastore.html == MockController.MINIFIED

    def test_skip_check(self):
        decorator = gae_html.cacheAndRender(skip_check=lambda controller: True)(MockController.get)
        response = decorator(self.controller)
        
        assert response is None
        assert self.controller.called

        from_memcache = memcache.get(MockController.PATH)
        assert from_memcache is None

    def test_cached_memcache(self):
        # test what happens when the response is already in memcache
        memcache.set(MockController.PATH, MockController.MINIFIED)

        decorator = gae_html.cacheAndRender()(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.MINIFIED
        assert not self.controller.called
        assert self.controller.response.unicode_body == MockController.MINIFIED

    def test_cached_datastore(self):
        # test what happens when the response is already in the datastore
        html_cache = gae_html.HTMLCache(id=MockController.PATH, html=MockController.MINIFIED)
        html_cache.put()

        decorator = gae_html.cacheAndRender(use_datastore=True)(MockController.get)
        response = decorator(self.controller)

        assert response == MockController.MINIFIED
        assert not self.controller.called
        assert self.controller.response.unicode_body == MockController.MINIFIED


class TestUtilities(BaseTestCase):

    def test_getFromDatastore(self):
        key = "test-key"
        html = "test text" + UCHAR
        assert gae_html.getFromDatastore(key) is None

        html_cache = gae_html.HTMLCache(id=key, html=html, expires=10)
        html_cache.put()
        from_datastore = gae_html.getFromDatastore(key)
        assert from_datastore is not None
        assert from_datastore == html

        html_cache.expires = 0
        html_cache.put()
        from_datastore = gae_html.getFromDatastore(key)
        assert from_datastore is None


class TestModel(BaseTestCase):

    def test_HTMLCache(self):
        html_cache = gae_html.HTMLCache(html="test text" + UCHAR, expires=10)
        html_cache.put()
        assert not html_cache.expired

        html_cache.expires = 0
        assert html_cache.expired


if __name__ == '__main__':
    unittest.main()
