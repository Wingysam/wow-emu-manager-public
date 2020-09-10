"""This package: Endpoint handlers. These handle page requests."""

#~# Dependencies #~#
import tornado.web

#~# Our own stuff #~#
from . index import IndexHandler


class DefaultHandler(IndexHandler):
    """Handle all other requests (the ones that don't have a unique handler)."""

    def get(self):
        self.send_message('404')


class ShutdownHandler(IndexHandler):
    """Handle shutdown command from web interface."""

    def get(self):
        if ( not self.DATA['USERNAME'] ):
            print( self.MSG_SYS['info_forbidden'] )
        elif ( self.check_perm() == 3 ):
            self.redirect("https://github.com/cmangos/")
            safe_exit( self.MSG_SYS['info_exit'] )
            return

        self.redirect( self.DATA['BASE_PATH'] )
