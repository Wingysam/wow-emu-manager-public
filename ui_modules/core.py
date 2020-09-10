from tornado.web import UIModule


class ReturnButton(UIModule):
    """Friggin return button. Friggin automagical."""

    def render(self):
        return self.render_string("module-return.html")


class SideNavMenu(UIModule):
    """Render navigation menu from list of pages"""

    def render(self):
        pages = { "news": "News" }
        return self.render_string("module-sidemenu.html", pages=pages)
