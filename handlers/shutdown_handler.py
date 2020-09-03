import tornado.web

from services import *

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

