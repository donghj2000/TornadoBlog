
#coding:utf-8

import os
import config
from handlers import User, Blog


urls = [
    (r"/api/user/",                       User.UserListHandler),
    (r"/api/user/(?P<user_id>\d+)/",      User.UserHandler),
    (r"/api/jwt_login",                   User.JwtLoginHandler),
    (r"/api/user/pwd",                    User.PasswordHandler),
    (r"/api/constant",                    User.GetConstantHandler),
    (r"/api/upload/(?P<path>.+)",         User.UploadImageHandler),
    (r"/account/result",                  User.AccountResultHandler),
    
    (r"/api/article/",                     Blog.AriticleListHandler),
    (r"/api/article/(?P<article_id>\d+)/", Blog.AriticleHandler),
    (r"/api/archive/",                    Blog.ArchiveListHandler),
    (r"/api/comment/",                    Blog.CommentListHandler),
    (r"/api/like/",                       Blog.LikeListHandler),
    (r"/api/message/",                    Blog.MessageListHandler),
    (r"/api/tag/",                        Blog.TagListHandler),
    (r"/api/tag/(?P<tag_id>\d+)/",         Blog.TagHandler),
    (r"/api/catalog/",                    Blog.CatalogListHandler),
    (r"/api/catalog/(?P<catalog_id>\d+)/", Blog.CatalogHandler),
    (r"/api/number/",                     Blog.NumberListHandler),
    (r"/api/top/",                        Blog.TopListHandler),
    (r"/api/es/",                         Blog.EsListHandler),
]