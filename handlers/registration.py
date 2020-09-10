from . import IndexHandler


class RegistrationHandler(IndexHandler):

    def get(self):
        if ( self.DATA['USERNAME'] ):
            self.redirect( self.DATA['BASE_PATH'] )
        elif ( self.DATA['REG_DISABLED'] ):
            self.send_message('reg_dis')
        else:
            self.render("register.html", DATA=self.DATA)

    def post(self):
        if ( self.DATA['REG_DISABLED'] ):
            self.send_message('reg_dis')
            return

        if ( not self.DATA['USERNAME'] ):
            regdata = self.get_credientals()

            # Same as with LoginHandler
            if (not regdata):
                self.send_message('reg_err')
                return

            # Check if account exists
            query = "SELECT `username` FROM `account` \
                     WHERE `username` = '{}'".format(regdata['login'])

            result = reach_db("realmd", query, "fetchone")

            if (result):
                self.send_message('reg_err')
                return

            # Register new account
            query = "INSERT INTO `account` (`username`, `sha_pass_hash`, `expansion`) \
                     VALUES ('{0}', '{1}', '{2}') \
            ".format( regdata['login'], regdata['hash'], self.DATA['DEFAULT_ADDON'] )

            reach_db("realmd", query, "fetchone")

            self.send_message('reg_ok')

        else:
            self.redirect( self.DATA['BASE_PATH'] )
