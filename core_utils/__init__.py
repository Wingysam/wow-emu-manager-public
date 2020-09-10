"""This package: Core Machinery."""

#~# Standard Py3 Libs #~#
import json

#~# Dependencies #~#
import tornado.ioloop


###########`
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

