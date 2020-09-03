import tornado.web

from services import *

class DefaultHandler(IndexHandler):
    """Handle all other requests (the ones that don't have a unique handler)."""

    def get(self):
        self.send_message('404')

