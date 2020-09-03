import tornado.web

from services import *

class NewsHandler(IndexHandler):
    """Fetch news entries and render them for user."""

    def get(self):
        self.DATA['news'] = get_news(15)

        self.render("news.html", DATA=self.DATA)
