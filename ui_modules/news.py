from tornado.web import UIModule


class FormatNews(UIModule):
    """Render news entry in a unified way."""

    def render(self, entries):
        return self.render_string("module-news.html", entries=entries)
