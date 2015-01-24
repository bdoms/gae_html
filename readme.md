Copyright &copy; 2010-2015, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE HTML is a small, simple tool to cache and minify HTML in GAE projects.

It removes comments and whitespace to reduce the amount of data when sending a response.
This should not effect validation or content of an HTML document.

Usage is simple. First, import:

```python
from gae_html import cacheAndRender
```

`cacheAndRender` is a decorator to place on an action to skip straight to returning the
cached version of a page, if it exists. Otherwise, it calls the action, takes the result,
caches it, and adds it to the response. For example:

```python
@cacheAndRender()
def get(self):
    # do some logic and handling of request
    return self.compile("template")
```

It automatically skips caching in obvious circumstances like during development
or if the user is an administrator.

Behavior is controlled through optional keyword arguments:

 * `expires` (int) default: 86400, number of seconds to cache for
 * `minify` (bool) default: True, whether to minify or not
 * `include_comments` (bool) default: False, whether to include comments or not when minifying
 * `use_datastore` (bool) default: False, whether to use the datastore as a fallback cache or not
 * `skip_check` (function(handler)) default: None, if present skips caching when returning `True`

A more complex example that avoids caching when errors are present in a session might look like:

```python
@cacheAndRender(skip_check=lambda handler: 'errors' in handler.session)
def get(self):
    # ...
```

Bug reports, feature requests, and patches are all welcome!
