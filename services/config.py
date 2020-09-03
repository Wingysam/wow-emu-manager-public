import json
from os import urandom as rnd

from services.core import safe_exit

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

    # Check if config needs to be adjusted
    if not ( local_CONFIG['SECRET']
        and local_CONFIG['DB_USER'] 
        and local_CONFIG['DB_PASS']
        and local_CONFIG['DB_NAME_CHARS']
        and local_CONFIG['DB_NAME_CORE']
        and local_CONFIG['DB_NAME_REALMD'] ):
        safe_exit( MSG_SYS['err_cfg_new'], False )

    return local_CONFIG

CONFIG = get_config()