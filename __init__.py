import os

from google.appengine.api import memcache, users

from htmlmin import HTMLMinifier

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')


def cacheHTML(controller, function, **kwargs):
    key = controller.request.path
    html = memcache.get(key)
    if html is None:
        html = function()
        # don't cache if in development or for admins
        if DEBUG and not users.is_current_user_admin():
            # cache for 1 day by default
            expires = kwargs.get("expires", 86400)
            minify = kwargs.get("minify", True)
            if minify:
                minifier = HTMLMinifier()
                minifier.feed(html)
                html = minifier.close()
            memcache.add(key, html, expires)
    return html


# decorator to skip straight to the cached version
def renderIfCached(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        key = controller.request.path
        html = memcache.get(key)
        # don't serve a cached version in development or to admins
        if html and not DEBUG and not users.is_current_user_admin():
            return controller.response.out.write(html)
        return action(*args, **kwargs)
    return decorate

