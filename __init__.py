import logging
import os
from datetime import datetime, timedelta

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

from htmlmin import HTMLMinifier

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')


# decorator to skip straight to the cached version, or cache it if it doesn't exist
def cacheAndRender(expires=86400, minify=True, include_comments=False,
        use_datastore=False, skip_check=None, content_type=None):

    def wrap_action(action):
        def decorate(*args,  **kwargs):
            controller = args[0]

            # if we're checking for errors and they're present, then return early to avoid caching
            if skip_check and skip_check(controller):
                return action(*args, **kwargs)

            key = controller.request.path + controller.request.query_string
            html = memcache.get(key)
            in_memcache = bool(html)

            in_datastore = False
            if not html and use_datastore:
                html = getFromDatastore(key)
                in_datastore = bool(html)

            if not html:
                action(*args, **kwargs)
                html = controller.response.unicode_body

            if html:
                if in_memcache or in_datastore:
                    # the action wasn't ever called, so explicitly render the output here
                    if content_type:
                        controller.response.headers['Content-Type'] = content_type
                    controller.response.write(html)

                # don't cache if in development or for admins
                if not DEBUG and not users.is_current_user_admin():
                    if minify and (not in_memcache or (use_datastore and not in_datastore)):
                        minifier = HTMLMinifier(include_comments=include_comments)
                        try:
                            minifier.feed(html)
                        except AssertionError:
                            logging.warning("HTML Parse Error: " + html)
                            minifier.output = ""
                        else:
                            html = minifier.close()

                    if not in_memcache:
                        memcache.add(key, html, expires)

                    if use_datastore and not in_datastore:
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
