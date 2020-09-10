"""This file: Utilities to access / work with a database."""

#~# Standard Py3 Libs #~#
from contextlib import contextmanager

#~# Dependencies #~#
import sqlite3
import mysql.connector as mariadb


def get_news(amount):
    """Return dictionary with certain amount of news entries in it."""
    query = "SELECT `text`, `header`, `timestamp` \
             FROM `news` ORDER BY `id` DESC LIMIT '{}'".format(amount)

    return reach_db("internal", query, "fetchall")

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
