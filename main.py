#!/usr/bin/python3

from os import urandom as rnd
import ssl
import json
import hashlib
import sqlite3

from contextlib import contextmanager

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import tornado.httpserver
import tornado.httpclient

import mysql.connector as mariadb
import handlers.modules as wow_emu_modules


from services import *
from routes import routes
from handlers import DefaultHandler, HTTPSRedirectHandler

#TODO import routes
#TODO import modules

def main():
    """Grab command line arguments, prepare environment and run the engine."""
    tornado.options.parse_command_line()

    # Dictionary of all modules used
    modules = { 'FormatNews': wow_emu_modules.FormatNews,
                'ReturnButton': wow_emu_modules.ReturnButton,
                'SideNavMenu': wow_emu_modules.SideNavMenu }

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

    # This closes DB connections at the end on it's own!
    with call_db() as conn_bundle:
        init_internal_db(conn_bundle) # FIXME: News Module, not yet.
        main()
