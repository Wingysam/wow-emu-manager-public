import tornado.web

from services import *

class HTTPSRedirectHandler(tornado.web.RequestHandler):
    """Handle HTTP -> HTTPS redirects."""

    def get(self):
        # FIXME: Can this part be abused?
        request = self.request.host
        if (':' in request):
            # Take the IP part only
            request = request.rsplit(":", 1)[0]

        if ( CONFIG['HTTPS_PORT'] != "443" ):
            request += ":" + CONFIG['HTTPS_PORT']

        self.redirect('https://' + request, permanent=False)
