#~# Standard Py3 libs #~#
import hashlib

#~# Dependencies #~#
import tornado.escape

from tornado.web import RequestHandler


class IndexHandler(RequestHandler):
    """Root page handler, it's what other handlers in here will inherit from."""

    #####################################################################
    # Below are "helper" methods that doesn't directly render anything. #
    #####################################################################

    def initialize(self, config, system_messages):
        """Allow you to __init__ everything you need for your subclass."""
        self.DATA = config
        self.MSG_SYS = system_messages
        # Check the user-cookie for active login and reject it in case
        # there are any special characters in it.
        if (self.current_user):
            if ( self.current_user.isalnum() ):
                self.DATA['USERNAME'] = tornado.escape.xhtml_escape(self.current_user)
        else:
            self.DATA['USERNAME'] = None

    def get_current_user(self):
        """Get username from secure cookie."""
        return self.get_secure_cookie("username")

    def get_credientals(self):
        """Grabs field data from forms.

        If it won't like any of the fields user will see an error message
        via send_message() and the function will return None, so handle it.
        """
        login_field = self.get_argument("l").upper()
        psswd_field = self.get_argument("p").upper()

        login_err = False

        # If username contains special characters...
        if ( not login_field.isalnum() ):
            login_err = True

        # If username or password are empty...
        if (not login_field or not psswd_field):
            login_err = True

        # If password is longer than...
        if (len(psswd_field) > 16):
            login_err = True

        # If username is longer than...
        if (len(login_field) > 16):
            login_err = True

        # If we don't like the credientals:
        if (login_err):
            return None

        # Calculate SHA1 of user:pass
        psswd_dough = login_field + ":" + psswd_field
        psswd_hash = hashlib.sha1( bytes(psswd_dough, "utf-8") ).hexdigest().upper()

        return { 'login': login_field, 'hash': psswd_hash, 'pass': psswd_field }

    def check_perm(self):
        """Return level of permissions for an account."""
        # We've already checked this for XSS. (In fact we do it _every_ time you get the page)
        # ...so now we are limiting SQLinj. This makes sense here, because account
        # creation rules are exactly similar, anyway.

        query = "SELECT `gmlevel` FROM `account` \
                 WHERE `username` = '{}'".format( self.DATA['USERNAME'] )

        return reach_db("realmd", query, "fetchone")['gmlevel']

    ###############################################
    # Below are things that directly render stuff #
    ###############################################

    def send_message(self, msg_handler):
        """Send a message wrapped in a nice template to the user."""

        msg_string = self.render_string( "messages/{}.html".format(msg_handler) )

        self.render("message.html", DATA=self.DATA, MESSAGE=msg_string)

    def get(self):
        """Process GET request from clients."""
        #self.DATA['news'] = get_news(3)
        self.render("index.html", DATA=self.DATA)
