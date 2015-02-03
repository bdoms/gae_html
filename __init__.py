import os
from datetime import datetime, timedelta

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

from htmlmin import HTMLMinifier

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')


# decorator to skip straight to the cached version, or cache it if it doesn't exist
def cacheAndRender(expires=86400, minify=True, include_comments=False,
        use_datastore=False, skip_check=None):

    minifier = None
    if minify:
        minifier = HTMLMinifier(include_comments=include_comments)

    def wrap_action(action):
        def decorate(*args,  **kwargs):
            controller = args[0]

            # if we're checking for errors and they're present, then return early to avoid caching
            if skip_check and skip_check(controller):
                return action(*args, **kwargs)

            key = controller.request.path + controller.request.query_string
            html = memcache.get(key)

            if not html and use_datastore:
                html = getFromDatastore(key)

            if not html:
                action(*args, **kwargs)
                html = controller.response.unicode_body

            if html:
                if minifier:
                    minifier.feed(html)
                    html = minifier.close()

                # don't cache if in development or for admins
                if not DEBUG and not users.is_current_user_admin():
                    memcache.add(key, html, expires)

                    if use_datastore:
                        html_cache = HTMLCache(id=key, html=html, expires=expires)
                        html_cache.put()

            return html
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
