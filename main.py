#!/usr/bin/python3

# WoW-Emu-Manager: A CMaNGOS management Web UI, written in Python.
"""This file: Site engine."""


# Let's be optimistic!... and so i was, back then. And it worked.
#
# But it's 2020 now. Repology says Py3.6 is the default on Ubuntu 18.04,
#   the LTS release at the time of writing, and this is what i'm going to use as baseline.
from sys import version_info as py_version

if py_version < (3, 6):
    exit("== This program requires Python 3.6+ to run, please update. Quitting... ==")


#~# Standard Py3 Libs #~#

from os import urandom as rnd
import ssl
import json
import hashlib
import sqlite3

from contextlib import contextmanager

#~# Dependencies #~#

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import tornado.httpserver
import tornado.httpclient

import mysql.connector as mariadb


###########
# Globals #
###########

MSG_SYS = { # Those below are console log messages.
            'err_cfg_generic': 'Your config file seems to be corrupted. Cannot continue.',
            'err_ssl_context': 'SSL Error: Cannot initiate SSL context. Check if your certificate- / key- files are valid.',
            'err_ssl_cert': 'SSL Error: Missing <fullchain.pem> and / or <privkey.pem> files from "certs/" folder.',
            'err_mysql_generic': 'Database Error: I don\'t know where to and- / or- what kind of DB you\'re trying to connect to, shutting down.',
            'err_cfg_new': 'You need to adjust default settings in config.json before running this program.',
            'info_exit': 'Shutting down...',
            'info_forbidden': 'Attempt to access forbidden internals -- ignoring...' }

###############
# EOF Globals #
###############


##################
# Core Machinery #
##################


def safe_exit(msg, turn_off_tornado=True):
    """Stop Tornado's IOLoop gracefully (if required) and then exit.

    If you don't need to turn tornado off (maybe you haven't started it yet?),
    supply False as second argument. It's optional, we stop tornado by default,
    so you are free to omit it.
    """
    print( "\n\n#=# {} #=#\n\n".format(msg) )

    if turn_off_tornado:
        this_loop = tornado.ioloop.IOLoop.current()

        this_loop.stop()
    else:
        exit()


def get_config():
    """Grab config file and return it as python object.

    Load config.json from current folder,
    create config if it doesn't exist, decode and return as dictionary.
    """
    # FIXME: Does this qualify as a hack?
    # For me it's an elegant way to avoid additional import.
    try:
        # If config.json exists -- open it for read access
        with open("config.json", mode="r", encoding="utf8") as config_file:
            # Decode JSON into Python ojbects
            local_CONFIG = json.loads( config_file.read() )

    except OSError:  # ...if we cannot open file for one reason or another -- write a new one.
        with open("config.json", mode="w", encoding="utf8") as config_file:
            # TODO: Rework config format into sectioned JSON.
            local_CONFIG = {  # Prepare the default config
                "SITENAME": "main",
                "DEVELOPER": False,
                "PAGE_TITLE": "WoW-Emu-Manager",
                "BASE_PATH": "/",
                "SECRET": rnd(128).hex(),  # FIXME: This will cause NotImplementedError in future, check docs.
                "SITE_PORT": "8000",       # N.B.: This is so because we prefer to be behind nginx or the like.
                "HTTPS": False,
                "HTTPS_PORT": "443",
                "DB_USER": "",
                "DB_PASS": "",
                "DB_ADDR": "127.0.0.1",
                "DB_PORT": "3306",
                "DB_NAME_CHARS": "",
                "DB_NAME_CORE": "",
                "DB_NAME_REALMD": "",
                "REG_DISABLED": False,
                "LOGIN_DISABLED": False,
                "DEFAULT_ADDON": 0 }

            # Encode Python objects into JSON string
            config_file.write( json.dumps(local_CONFIG, indent=4) )

    except json.decoder.JSONDecodeError:
        safe_exit( MSG_SYS['err_cfg_generic'], False )

    config_error = False

    # Check if config needs to be adjusted
    if ( not local_CONFIG['SECRET'] ):
        config_error = True
    if ( not local_CONFIG['DB_USER'] ):
        config_error = True
    if ( not local_CONFIG['DB_PASS'] ):
        config_error = True
    if ( not local_CONFIG['DB_NAME_CHARS'] ):
        config_error = True
    if ( not local_CONFIG['DB_NAME_CORE'] ):
        config_error = True
    if ( not local_CONFIG['DB_NAME_REALMD'] ):
        config_error = True

    if (config_error):
        safe_exit( MSG_SYS['err_cfg_new'], False )

    return local_CONFIG


@contextmanager
def call_db():
    """Grab DB connections, yield a dictionary with mapped connection objects.

    Because of @contextmanager, we can use `with` and properly close handles.
    """
    tmp_cfg = {  # FIXME: It is assumed that you use one user to access all three DB
        'host': CONFIG['DB_ADDR'],
        'port': CONFIG['DB_PORT'],
        'user': CONFIG['DB_USER'],
        'password': CONFIG['DB_PASS'] }

    conns = { 'internal': sqlite3.connect('internal.db'),
              'chars': mariadb.connect(database=CONFIG['DB_NAME_CHARS'], **tmp_cfg),
              'core': mariadb.connect(database=CONFIG['DB_NAME_CORE'], **tmp_cfg),
              'realmd': mariadb.connect(database=CONFIG['DB_NAME_REALMD'], **tmp_cfg) }

    try:
        yield conns

    except mariadb.Error as error:
        print(error)

    finally:
        conns['chars'].close()
        conns['core'].close()
        conns['realmd'].close()
        conns['internal'].close()


def init_internal_db():
    """Initialize internal sqlite DB structure."""
    # We are working with internal DB
    db_cur = conn_bundle['internal'].cursor()

    # If there's no table named "news" we create one
    try:
        db_cur.execute("SELECT * FROM `news` LIMIT 1")

    except sqlite3.OperationalError:
        query = """CREATE TABLE `news` (
            `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `text` TEXT,
            `header` TEXT,
            `timestamp` TEXT )"""

        db_cur.execute(query)


def reach_db(db_name, query, mode):
    """Execute a query against connected DB and return the result.

    Arguments:
        db_conn     Connection object to attach cursor to.
                    Possible values are:
                    "chars", "core", "realmd", "internal"

        query       Query string to run against the DB.

        mode        "fetchall" or "fetchone" respectively.
    """
    # If an error occurs -- return object None
    results = None

    try:
        db_conn = conn_bundle[db_name]

        # Enter the DB in question using either of the cursors for respective
        # DB drivers: SQLite3 or MySQL-Connector-Python
        if (db_name == "internal"):
            db_conn.row_factory = sqlite3.Row
            db_cur = db_conn.cursor()
        else:
            db_cur = db_conn.cursor(dictionary=True)

        db_cur.execute(query)
        # Walk over results
        if (mode == "fetchone"):
            results = db_cur.fetchone()
        elif (mode == "fetchall"):
            results = db_cur.fetchall()
        else:
            results = None

    except mariadb.Error:
        safe_exit( MSG_SYS['err_mysql_generic'] )

    except sqlite3.OperationalError as err:
        print(err)

    return results


def get_news(amount):
    """Return dictionary with certain amount of news entries in it."""
    query = "SELECT `text`, `header`, `timestamp` \
             FROM `news` ORDER BY `id` DESC LIMIT '{}'".format(amount)

    return reach_db("internal", query, "fetchall")


def main():
    """Grab command line arguments, prepare environment and run the engine."""
    tornado.options.parse_command_line()

    # Dictionary of all modules used
    modules = { 'FormatNews': FormatNews,
                'ReturnButton': ReturnButton,
                'SideNavMenu': SideNavMenu }

    # Change this in configs if you're hosting behind some kind of proxy (nginx!)
    base_path = CONFIG['BASE_PATH']

    # Tornado webserver settings
    settings = { 'template_path': "templates/" + CONFIG['SITENAME'],
                 'static_path': "static/" + CONFIG['SITENAME'],
                 'cookie_secret': CONFIG['SECRET'],
                 'xsrf_cookies': True,
                 'autoreload': False,
                 'ui_modules': modules,
                 'default_handler_class': DefaultHandler,
                 'compiled_template_cache': True }

    # Makes your life easier.
    if ( CONFIG['DEVELOPER'] ):
        # No need to restart the core each time you update templates.
        settings['compiled_template_cache'] = False
        settings['autoreload'] = True

    # Make an instance of web app and connect
    # some handlers to respective URL path regexps
    routes = [ (base_path, IndexHandler, None, "/"),
               (base_path + r"static/(.*)", tornado.web.StaticFileHandler, { "path": "static/" + CONFIG['SITENAME'] } ),
               (base_path + r"shutdown", ShutdownHandler),
               (base_path + r"login", LoginHandler),
               (base_path + r"logout", LogoutHandler),
               (base_path + r"register", RegistrationHandler),
               (base_path + r"profile", ProfileHandler),
               (base_path + r"news", NewsHandler) ]

    site = tornado.web.Application(handlers=routes, **settings)

    if ( CONFIG['HTTPS'] ):
        # Prepare SSL
        ssl_context = ssl.SSLContext()

        # Attempt to load SSL certificate and key
        try:
            ssl_context.load_cert_chain("certs/fullchain.pem", "certs/privkey.pem")

        except ssl.SSLError:
            safe_exit( MSG_SYS['err_ssl_context'] )
            return

        except FileNotFoundError:
            safe_exit( MSG_SYS['err_ssl_cert'] )
            return

        https_server = tornado.httpserver.HTTPServer(site, ssl_options=ssl_context)
        https_server.listen( CONFIG['HTTPS_PORT'] )

    else:
        https_server = None

    # Spawn HTTP -> HTTPS redirect handler
    if (https_server):
        site = tornado.web.Application( handlers=[ (r"/.*", HTTPSRedirectHandler) ] )

    http_server = tornado.httpserver.HTTPServer(site)
    http_server.listen( CONFIG['SITE_PORT'] )

    # Main event and I/O loop. Any code AFTER this should use safe_exit()
    tornado.ioloop.IOLoop.current().start()


######################
# EOF Core Machinery #
######################


#########################################
# Handlers: These handle page requests. #
#########################################


class IndexHandler(tornado.web.RequestHandler):
    """Root page handler, it's what other handlers in here will inherit from."""

    #####################################################################
    # Below are "helper" methods that doesn't directly render anything. #
    #####################################################################

    def initialize(self):
        """Allow you to __init__ everything you need for your subclass."""
        self.DATA = {}
        self.DATA['PAGE_TITLE'] = CONFIG['PAGE_TITLE']
        self.DATA['BASE_PATH'] = CONFIG['BASE_PATH']

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


class DefaultHandler(IndexHandler):
    """Handle all other requests (the ones that don't have a unique handler)."""

    def get(self):
        self.send_message('404')


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


class LogoutHandler(IndexHandler):

    def get(self):
        if( self.DATA['USERNAME'] ):
            self.clear_cookie("username")

        self.redirect( self.DATA['BASE_PATH'] )


class RegistrationHandler(IndexHandler):

    def get(self):
        if ( self.DATA['USERNAME'] ):
            self.redirect( self.DATA['BASE_PATH'] )
        elif ( CONFIG['REG_DISABLED'] ):
            self.send_message('reg_dis')
        else:
            self.render("register.html", DATA=self.DATA)

    def post(self):
        if ( CONFIG['REG_DISABLED'] ):
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
            ".format( regdata['login'], regdata['hash'], CONFIG['DEFAULT_ADDON'] )

            reach_db("realmd", query, "fetchone")

            self.send_message('reg_ok')

        else:
            self.redirect( self.DATA['BASE_PATH'] )


class ProfileHandler(IndexHandler):

    def get(self):
        if ( self.DATA['USERNAME'] ):
            self.send_message('404')
        else:
            self.redirect( self.DATA['BASE_PATH'] )


class NewsHandler(IndexHandler):
    """Fetch news entries and render them for user."""

    def get(self):
        self.DATA['news'] = get_news(15)

        self.render("news.html", DATA=self.DATA)


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


################
# EOF Handlers #
################


#####################################################################
# Modules: Embeddable widgets of stuff with flexible functionality. #
#####################################################################

class FormatNews(tornado.web.UIModule):
    """Render news entry in a unified way."""

    def render(self, entries):
        return self.render_string("module-news.html", entries=entries)


class ReturnButton(tornado.web.UIModule):
    """Friggin return button. Friggin automagical."""

    def render(self):
        return self.render_string("module-return.html")


class SideNavMenu(tornado.web.UIModule):
    """Render navigation menu from list of pages"""

    def render(self):
        pages = { "news": "News" }
        return self.render_string("module-sidemenu.html", pages=pages)


###############
# EOF Modules #
###############


if __name__ == "__main__":  # Make sure we aren't being used as someone's module!
    CONFIG = get_config()

    # This closes DB connections at the end on it's own!
    #with call_db() as conn_bundle:
    #    init_internal_db() # FIXME: News Module, not yet.
    main()
