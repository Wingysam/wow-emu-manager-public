import tornado.web

from handlers import *
from services import CONFIG

base_path = CONFIG['BASE_PATH']
sitename = 'static/' + CONFIG['SITENAME']

routes = [ 
  (base_path, IndexHandler, None, "/"),
  (base_path + r"static/(.*)", tornado.web.StaticFileHandler, { "path": sitename } ),
  (base_path + r"shutdown", ShutdownHandler),
  (base_path + r"login", LoginHandler),
  (base_path + r"logout", LogoutHandler),
  (base_path + r"register", RegistrationHandler),
  (base_path + r"profile", ProfileHandler),
  (base_path + r"news", NewsHandler) ]

            