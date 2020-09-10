from . import IndexHandler


class ProfileHandler(IndexHandler):

    def get(self):
        if ( self.DATA['USERNAME'] ):
            self.send_message('404')
        else:
            self.redirect( self.DATA['BASE_PATH'] )
