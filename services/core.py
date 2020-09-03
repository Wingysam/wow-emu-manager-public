import tornado.ioloop

"""Stop Tornado's IOLoop gracefully (if required) and then exit.

If you don't need to turn tornado off (maybe you haven't started it yet?),
supply False as second argument. It's optional, we stop tornado by default,
so you are free to omit it.
"""
def safe_exit(msg, turn_off_tornado=True):
    print( "\n\n#=# {} #=#\n\n".format(msg) )

    if turn_off_tornado:
        this_loop = tornado.ioloop.IOLoop.current()

        this_loop.stop()
    else:
        exit()

