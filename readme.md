Copyright &copy; 2010-2015, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE HTML is a small, simple tool to cache and minify HTML in GAE projects.

It removes comments and whitespace to reduce the amount of data when sending a response.
This should not effect validation or content of an HTML document.

Usage is simple. First, import:

```python
from gae_html import cacheHTML, renderIfCached
```

`cacheHTML` takes a `RequestHandler` and a function to produce the HTML as its arguments.
Optional keyword arguments include:

 * `expires` (int) default: 86400, number of seconds to cache for
 * `minify` (bool) default: True, whether to minify or not
 * `use_datastore` (bool) default: False, whether to use the datastore as a fallback cache or not
 * `include_comments` (bool) default: False, whether to include comments or not

To use it in the render method for your controller or handler, do something like:

```python
def render(self, template, **kwargs):
    def renderHTML:
        return self.compileTemplate(template, **kwargs)
    html = cacheHTML(self, renderHTML)
    self.reponse.out.write(html)
```

This takes care of the caching side of things, and `cacheHTML` automatically skips caching
in obvious circumstances like during development or if the user is an administrator.

`renderIfCached` is a decorator to place on an action to skip straight to returning the
cached version of a page, if desired. It works like this:

```python
@renderIfCached()
def get(self):
    # do some logic and handling of request
    self.render("template")
```

Bug reports, feature requests, and patches are all welcome!
