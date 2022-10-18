#coding:utf-8

import json
import jwt
from tornado.web import RequestHandler
from utils.util import jwt_encode,jwt_decode
import config

class BaseHandler(RequestHandler):
    """handler 基类"""
    @property
    def dbUtil(self):
        return self.application.dbUtil

    @property
    def redis(self):
        return self.application.redis
    
    def prepare(self):
        """"""
        self.xsrf_token
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            self.json_args = json.loads(self.request.body)
        else:
            self.json_args = {}
    def write_error(self, status_code, **kwargs):
        pass

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, PUT, PATCH, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
        self.set_header("Access-Control-Expose-Headers", "Content-Type")

    def options(self):
        self.set_status(204)
        self.finish()

    def initialize(self):
        pass
        
    def on_finish(self):
        pass
        
    def get_current_user(self):
        token = self.get_cookie(config.JWT_AUTH_COOKIE, None)
        if not token:
            return self.my_write_error(dict(detail='No Authorization'),401)

        try:
            payload = jwt_decode(token)
        except jwt.InvalidTokenError as e:
            self.my_write_error(dict(detail="权限非法!"), 403)
            return None
        except jwt.ExpiredSignatureError as e:
            self.my_write_error(dict(detail="权限过期!"), 403)
            return None
            
        identity = payload.get("identity")   
        if identity is None:
            self.my_write_error(dict(detail='未登陆'), 405)
            
        return identity
        
    def my_write_error(self, content, error_code):
       self.set_status(error_code)
       self.write(content)
