import logging
import os
from datetime import datetime, timedelta

from .htmlmin import HTMLMinifier

DEBUG = os.getenv('GAE_ENV', 'localdev').startswith('localdev')

CACHE_CONTENT = {}
CACHE_TIME = {}


# decorator to skip straight to the cached version, or cache it if it doesn't exist
def cacheAndRender(expires=86400, minify=True, include_comments=False, skip_check=None, content_type=None):

    def wrap_action(action):
        def decorate(*args,  **kwargs):
            controller = args[0]

            # if we're checking for errors and they're present, then return early to avoid caching
            if skip_check and skip_check(controller):
                return action(*args, **kwargs)

            # NOTE that the controller interface is assuming Tornado
            key = controller.request.path + controller.request.query
            html = None
            if key in CACHE_CONTENT:
                # check if expired and remove if it is
                if CACHE_TIME[key] < datetime.utcnow() - timedelta(seconds=expires):
                    del CACHE_CONTENT[key]
                    del CACHE_TIME[key]
                else:
                    html = CACHE_CONTENT[key]

            if html:
                # the action wasn't ever called, so explicitly render the output here
                if content_type:
                    controller.set_header('Content-Type', content_type)
                controller.write(html)
            else:
                action(*args, **kwargs)
                html = b"".join(controller._write_buffer).decode()

                if minify:
                    minifier = HTMLMinifier(include_comments=include_comments)
                    try:
                        minifier.feed(html)
                    except AssertionError:
                        logger = logging
                        if hasattr(controller, 'logger'):
                            logger = controller.logger
                        logger.warning('HTML Parse Error: ' + html)
                        minifier.output = ''
                    else:
                        html = minifier.close()

                # don't cache if in development
                if html and not DEBUG:
                    CACHE_CONTENT[key] = html
                    CACHE_TIME[key] = datetime.utcnow()

            # can't return anything here - causes a yield error in Tornado
        return decorate
    return wrap_action


def clearCache():
    global CACHE_CONTENT, CACHE_TIME
    CACHE_CONTENT = {}
    CACHE_TIME = {}
