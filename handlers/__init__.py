"""This package: Endpoint handlers. These handle page requests."""

#~# Dependencies #~#
import tornado.web

#~# Our own stuff #~#
from . index import IndexHandler


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


class DefaultHandler(IndexHandler):
    """Handle all other requests (the ones that don't have a unique handler)."""

    def get(self):
        self.send_message('404')


class ShutdownHandler(IndexHandler):
    """Handle shutdown command from web interface."""

    def get(self):
        if ( not self.DATA['USERNAME'] ):
            print( MSG_SYS['info_forbidden'] )
        elif ( self.check_perm() == 3 ):
            self.redirect("https://github.com/cmangos/")
            safe_exit( MSG_SYS['info_exit'] )
            return

        self.redirect( self.DATA['BASE_PATH'] )
