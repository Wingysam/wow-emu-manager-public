import tornado.web

class FormatNews(tornado.web.UIModule):
    """Render news entry in a unified way."""

    def render(self, entries):
        return self.render_string("module-news.html", entries=entries)


class ReturnButton(tornado.web.UIModule):
    """Friggin return button. Friggin automagical."""

    def render(self):
        return self.render_string("module-return.html")


class SideNavMenu(tornado.web.UIModule):
    """Render navigation menu from list of pages"""

    def render(self):
        pages = { "news": "News" }
        return self.render_string("module-sidemenu.html", pages=pages)

