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

#~# Our own python modules #~#
from handlers import *

from handlers.auth import *
from handlers.registration import *
from handlers.profile import *
from handlers.index import *
from handlers.news import *

from ui_modules.core import *
from ui_modules.news import *


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
    index_cfg = { "config": CONFIG }
    routes = [ (base_path, IndexHandler, index_cfg, "/"),
               (base_path + r"static/(.*)", tornado.web.StaticFileHandler, { "path": "static/" + CONFIG['SITENAME'] } ),
               (base_path + r"shutdown", ShutdownHandler, index_cfg),
               (base_path + r"login", LoginHandler, index_cfg),
               (base_path + r"logout", LogoutHandler, index_cfg),
               (base_path + r"register", RegistrationHandler, index_cfg),
               (base_path + r"profile", ProfileHandler, index_cfg),
               (base_path + r"news", NewsHandler, index_cfg) ]

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


if __name__ == "__main__":  # Make sure we aren't being used as someone's module!
    CONFIG = get_config()

    # This closes DB connections at the end on it's own!
    #with call_db() as conn_bundle:
    #    init_internal_db() # FIXME: News Module, not yet.
    main()
