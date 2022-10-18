#coding:utf-8
import os,sys
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpserver
import config
from utils.MySQLUtil import  MySQLdbUtil

from urls import urls
from tornado.options import options, define
from tornado.web import RequestHandler

define("port", type=int, default=8000, help="run server on the ginven port")

parentdir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,parentdir)


class Application(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.dbUtil = MySQLdbUtil(**config.mysql_options)

def main():
    options.log_file_prefix = config.log_file
    options.logging = config.log_level
    tornado.options.parse_command_line()
    app = Application(
        urls,
        **config.settings
    )
    print("listening on port ", options.port)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
    print("listening on port ", options.port)
if __name__ == "__main__":
    main()
