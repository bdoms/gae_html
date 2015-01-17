import os
from datetime import datetime, timedelta

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

from htmlmin import HTMLMinifier

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')



def cacheHTML(controller, function, **kwargs):
    key = controller.request.path + controller.request.query_string
    html = memcache.get(key)

    if not html:
        use_datastore = kwargs.get("use_datastore", False)
        if use_datastore:
            html = getFromDatastore(key)

    if not html:
        html = function()

        # don't cache if in development or for admins
        if not DEBUG and not users.is_current_user_admin():
            # cache for 1 day by default
            expires = kwargs.get("expires", 86400)
            minify = kwargs.get("minify", True)
            if minify:
                include_comments = kwargs.get("include_comments", False)
                minifier = HTMLMinifier(include_comments=include_comments)
                minifier.feed(html)
                html = minifier.close()

            memcache.add(key, html, expires)

            if use_datastore:
                html_cache = HTMLCache(id=key, html=html, expires=expires)
                html_cache.put()

    return html


# decorator to skip straight to the cached version
def renderIfCached(use_datastore=False):
    def wrap_action(action):
        def decorate(*args,  **kwargs):
            controller = args[0]
            key = controller.request.path + controller.request.query_string
            html = memcache.get(key)
            if not html and use_datastore:
                html = getFromDatastore(key)
            # don't serve a cached version in development or to admins
            if html and not DEBUG and not users.is_current_user_admin():
                return controller.response.out.write(html)
            return action(*args, **kwargs)
        return decorate
    return wrap_action


def getFromDatastore(key):
    # don't use memcache with NDB here so it doesn't interfere with the identical key
    # we'd rather have the text returned right away from the direct caching vs. having this entity cached
    html = None
    html_cache = HTMLCache.get_by_id(key, use_memcache=False)
    if html_cache:
        if html_cache.expired:
            html_cache.key.delete()
        else:
            html = html_cache.html
    return html


class HTMLCache(ndb.Model):
    html = ndb.TextProperty(required=True)
    expires = ndb.IntegerProperty(default=86400)
    timestamp = ndb.DateTimeProperty(auto_now_add=True)

    @property
    def expired(self):
        return self.timestamp + timedelta(seconds=self.expires) < datetime.utcnow()
