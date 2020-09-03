import tornado.web

from services import *

class LoginHandler(IndexHandler):

    def post(self):
        if ( CONFIG['LOGIN_DISABLED'] ):
            self.send_message('login_err')
            return

        if ( self.DATA['USERNAME'] ):
            self.redirect( self.DATA['BASE_PATH'] )
            return

        logindata = self.get_credientals()

        if (not logindata):
            self.send_message('login_err')
            return

        query = "SELECT `username` FROM `account` \
                 WHERE `username` = '{0}' AND `sha_pass_hash` = '{1}' \
                 ".format(logindata['login'], logindata['hash'])

        result = reach_db("realmd", query, "fetchone")

        # Idea is that our query will be empty if it won't find an account+hash
        # pair, while Tornado handles all escaping
        if (result):
            self.set_secure_cookie("username", logindata['login'])
        else:
            self.send_message('login_err')
            return

        self.redirect( self.DATA['BASE_PATH'] )
