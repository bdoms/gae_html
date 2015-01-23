
import re
import logging
from HTMLParser import HTMLParser

WHITESPACE = re.compile(r"\s+")


class HTMLMinifier(HTMLParser):

    def __init__(self, include_comments=False):
        HTMLParser.__init__(self)
        self.include_comments = include_comments
        self.output = ""
        self.pre = False

    def error(self, message):
        logging.error(message)

    def handle_starttag(self, tag, attributes):
        if tag.lower() == "pre":
            self.pre = True
        self.output += self.get_starttag_text()

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def handle_endtag(self, tag):
        if tag.lower() == "pre":
            self.pre = False
        self.output += "</" + tag + ">"

    def handle_data(self, data):
        if not self.pre:
            # remove whitespace by replacing any one or more occurence of it with a single space
            data = re.sub(WHITESPACE, " ", data)
        self.output += data

    def handle_comment(self, data):
        # get rid of all comments by returning nothing if they aren't enabled
        if self.include_comments:
            self.output += "<!--" + data + "-->"
        return

    def handle_decl(self, decl):
        self.output += "<!" + decl + ">"

    def handle_charref(self, name):
        self.output += "&#" + name + ";"

    def handle_entityref(self, name):
        self.output += "&" + name + ";"

    def close(self):
        HTMLParser.close(self)
        final = self.output
        self.output = ""
        return final
