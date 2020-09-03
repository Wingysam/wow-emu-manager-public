import tornado.web

from services import *

class LogoutHandler(IndexHandler):

    def get(self):
        if( self.DATA['USERNAME'] ):
            self.clear_cookie("username")

        self.redirect( self.DATA['BASE_PATH'] )
