#coding:utf-8
import datetime
import os
DEBUG = True

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "upload"),
    "template_path":os.path.join(os.path.dirname(__file__), "template"),
    "static_url_prefix": "/upload/",
    #"cookie_secret": "vCJcd6ypQOCDwh7XRG/eXpaofbJNE0eCpYA5+qFVXoI=",
    #"xsrf_cookies" : True,
    "debug":True
}

mysql_options = dict(
    host = "127.0.0.1",
    database="tornadoblog",
    user = "root",
    password = "123456",
    port = 3306,
    charset = "utf8", 
    use_unicode = True
)

redis_options = dict(
    host = "127.0.0.1",
    port = 6379
)

log_file = os.path.join(os.path.dirname(__file__), "logs/log")
log_level = "debug"

session_expires = 86400

#√‹¬Îº”√‹√‹‘ø
passwd_hash_key = "nlgCjaTXQX2jpupQFQLoQo5N4OkEmkeHsHD9+BBx2WQ="



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_ROOT = os.path.join(BASE_DIR, 'upload')
MEDIA_URL = "../upload"
UPLOAD_URL = 'upload'


JWT_SECRET_KEY = "alita666666"
JWT_EXPIRATION_DAYS = 7
JWT_VERIFY_CLAIMS = ['signature', 'exp', 'iat']
JWT_REQUIRED_CLAIMS = ['exp', 'iat']
JWT_AUTH_COOKIE= "JwtCookie"
JWT_ALGORITHM = 'HS256'
JWT_LEEWAY = datetime.timedelta(seconds=10)
JWT_NOT_BEFORE_DELTA = datetime.timedelta(seconds=0)

SECRET_KEY = '3p--&e$%^%71)ijd@td7e2=s9gdlxalogjkor@_f#@47+sc=qo'
HOST_SITE = "127.0.0.1:8000"
MAIL_SERVER = "smtp.qq.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'xxxxxxxx@qq.com'
MAIL_PASSWORD = 'asdfasggdgsdf'

ELASTICSEARCH_ON = True
ELASTICSEARCH_HOST = "127.0.0.1:9200"
ELASTICSEARCH_INDEX = "tornadoblog"