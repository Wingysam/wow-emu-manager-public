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
import ssl

from os import urandom as rnd

#~# Dependencies #~#
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import tornado.httpserver
import tornado.httpclient

#~# Our own python modules #~#
# FIXME: Get rid of as many from-imports as you can,
#        namespaces are one honking great idea -- let's use more of those!
from core_utils import *
from core_utils.db import *

from handlers import *

from handlers.auth import *
from handlers.registration import *
from handlers.profile import *
from handlers.index import *
from handlers.news import *

# TODO: This is no longer has to be imported like this,
#       just import it and pass through settings
from ui_modules.core import *
from ui_modules.news import *


def Entrypoint():
    """Grab command line arguments, prepare environment and run the engine."""
    tornado.options.parse_command_line()

    # Dictionary of all modules used
    modules = { 'FormatNews': FormatNews,
                'ReturnButton': ReturnButton,
                'SideNavMenu': SideNavMenu }

    # Change this in configs if you're hosting behind some kind of proxy (nginx!)
    base_path = CONFIG['BASE_PATH']

    index_cfg = { "config": CONFIG, "system_messages": MSG_SYS }

    # Tornado webserver settings
    settings = { 'template_path': "templates/" + CONFIG['SITENAME'],
                 'static_path': "static/" + CONFIG['SITENAME'],
                 'cookie_secret': CONFIG['SECRET'],
                 'xsrf_cookies': True,
                 'autoreload': False,
                 'ui_modules': modules,  # TODO: Just give it ui_modules, instead
                 'default_handler_class': DefaultHandler,
                 'default_handler_args': index_cfg,
                 'compiled_template_cache': True }

    # Makes your life easier.
    if ( CONFIG['DEVELOPER'] ):
        # No need to restart the core each time you update templates.
        settings['compiled_template_cache'] = False
        settings['autoreload'] = True

    # Make an instance of web app and connect
    # some handlers to respective URL path regexps
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


if __name__ == "__main__":  # Make sure we aren't being used as someone's module!
    CONFIG = get_config()

    # This closes DB connections at the end on it's own!
    #with call_db() as conn_bundle:
    #    init_internal_db() # FIXME: News Module, not yet.
    Entrypoint()
