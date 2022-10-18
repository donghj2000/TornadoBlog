#coding:utf-8
import logging
import hashlib
import config
from datetime import datetime
from tornado.web import RequestHandler
from .BaseHandler import BaseHandler
from utils.util import jwt_encode,jwt_decode, encrypt,\
    get_sha256,send_mail, get_random_password, get_upload_file_path


class UserListHandler(BaseHandler):
    def get(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
                            
            username     = self.get_query_argument("username", None)
            is_active    = self.get_query_argument("is_active", None)
            is_superuser = self.get_query_argument("is_superuser", None)
            page         = self.get_query_argument("page", "1")
            page_size    = self.get_query_argument("page_size", "10")

            sql = "select * from blog_user "
            params = []
            sql_where = []
            if username != None and username != "":
                sql_where.append("username = %s ")
                params.append(username.encode("utf-8"))
            if is_active != None:
                sql_where.append("is_active = %s ")
                if is_active == "true":
                    params.append(1)
                else:
                    params.append(0)
            
            if is_superuser != None:
                sql_where.append("is_superuser = %s ")
                if is_superuser == "true":
                    params.append(1)
                else:
                    params.append(0)
            
            if len(sql_where)!=0:
                sql += "where "
                sql += " and ".join(sql_where)
            
            sql += "limit %s offset %s"
            params.append(int(page_size))
            params.append(((int(page) - 1) * int(page_size)))
            users = self.dbUtil.select_many(sql, params)            
        except Exception as ex:
            print("ex,", ex)
            self.my_write_error({"detail": "内部错误"}, 500)
            return 
         
        if users == None or len(users) == 0:    
            self.my_write_error({"detail": "没有用户"}, 500)
            return
            
        resp = {
            "count": len(users),
            "results": [{
                 "id":           user["id"], 
                 "username":     user["username"], 
                 "last_login":   user["last_login"].strftime('%Y-%m-%d %H:%M:%S') if user["last_login"]!=None else "", 
                 "email":        user["email"],
                 "avatar":       user["avatar"],
                 "nickname":     user["nickname"],
                 "is_active":    True if user["is_active"]==1 else False, 
                 "is_superuser": True if user["is_superuser"]==1 else False,
                 "created_at":   user["created_at"].strftime('%Y-%m-%d %H:%M:%S') if user["created_at"]!=None else ""
            } for user in users]
        }            
        self.write(resp)
        
    def post(self):
        try:
            username = self.json_args.get("username")
            password = self.json_args.get("password")
            nickname = self.json_args.get("nickname")
            avatar   = self.json_args.get("avatar")
            email    = self.json_args.get("email")
            desc     = self.json_args.get("desc")
            print("nickname", nickname,type(nickname))
            
            if not all([username, password, email]):
                return  self.my_write_error(dict(detail="参数不完整"), 500)
        
            passwd = encrypt(password)
            sql = "insert into blog_user(username, password, is_superuser, is_active, email, avatar, nickname, description) values(%s, %s, %s, %s, %s, %s, %s, %s)"
            count = self.dbUtil.insert_operation(sql, (username, passwd, 0, 0, email, avatar, nickname, desc))
            user  = self.dbUtil.select_one("select * from blog_user where username = %s",(username,))
        except Exception as e:
            logging.error(e)
            print("e,",e)
            return self.my_write_error(dict(detail="用户已存在"), 500)
        
        sign = get_sha256(get_sha256(config.SECRET_KEY + str(user["id"])))
        site = config.HOST_SITE
        if config.DEBUG:
            site = '127.0.0.1:8000'
        path = '/account/result'
        url = "http://{site}{path}?type=validation&id={id}&sign={sign}".format(
            site=site, path=path, id=user["id"], sign=sign)
        content = """
                        <p>请点击下面链接验证您的邮箱</p>
                        <a href="{url}" rel="bookmark">{url}</a>
                        再次感谢您！
                        <br />
                        如果上面链接无法打开，请将此链接复制至浏览器。
                        {url}
                        """.format(url=url)
        
        print(content)
        try:
            send_mail(subject="验证您的电子邮箱",
                      message=content,
                      recipient_list=[user["email"]])
                    
            self.write({"detail": "向你的邮箱发送了一封邮件，请打开验证，完成注册。"})
        except Exception as e:
            print("exception:", e)
            self.my_write_error({"detail": "发送验证邮箱失败，请检查邮箱是否正确。"}, 500)
        
class UserHandler(BaseHandler):
    def get(self, user_id):
        try:
            user_id = int(user_id)
            curr_user = self.get_current_user()
            if not curr_user:
                return
            if not curr_user["is_superuser"] and curr_user["id"] != user_id:
                return self.my_write_error(dict(detail = "只能获取自己的个人信息"), 400)
            user = self.dbUtil.select_one("select * from blog_user where id = %s", (user_id,))
            if not user:
                return self.my_write_error(dict(detail = "用户不存在"), 500)
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error(dict(detail = "内部错误"), 500)
            
        resp =  {"id":           user["id"], 
                 "username":     user["username"], 
                 "last_login":   user["last_login"].strftime('%Y-%m-%d %H:%M:%S') if user["last_login"]!=None else "", 
                 "email":        user["email"],
                 "avatar":       user["avatar"],
                 "nickname":     user["nickname"],
                 "is_active":    True if user["is_active"]==1 else False, 
                 "is_superuser": True if user["is_superuser"]==1 else False,
                 "created_at":   user["created_at"].strftime('%Y-%m-%d %H:%M:%S') if user["created_at"]!=None else "" }
        
        self.write(resp)
    
    def put(self,user_id):
        try:
            user_id = int(user_id)
            curr_user = self.get_current_user()
            if not curr_user:
                return
            if not curr_user["is_superuser"] and curr_user["id"] != user_id:
                return self.my_write_error(dict(detail = "只能获取自己的个人信息"), 400)

            nickname = self.json_args.get("nickname")
            avatar   = self.json_args.get("avatar")
            email    = self.json_args.get("email")
            desc     = self.json_args.get("desc")
            is_active= self.json_args.get("is_active")

            sql = "update blog_user "
            params = []
            sql_where = []
            if nickname != None and nickname != "":
                sql_where.append("nickname = %s ")
                params.append(nickname)
            if avatar != None and avatar != "":
                sql_where.append("avatar = %s ")
                params.append(avatar)
            if email != None and email != "":
                sql_where.append("email = %s ")
                params.append(email)
            if desc != None and desc != "":
                sql_where.append("description = %s ")
                params.append(desc)
            if is_active != None:
                sql_where.append("is_active = %s ")
                if is_active == True:
                    params.append(1)
                else:
                    params.append(0)
            if len(sql_where)!=0:
                sql += "set "
                sql += ", ".join(sql_where)
            sql += " where id = %s"
            params.append(user_id)   
            count = self.dbUtil.update_operation(sql, params)
        except Exception as e:
            logging.error(e)
            print("e,",e)
            return self.my_write_error(dict(detail="用户已存在"), 500)

        self.write(dict(detail="修改个人信息成功!"))
        
    def patch(self,user_id):
        self.put(user_id)

class JwtLoginHandler(BaseHandler):
    def post(self):
        try:
            username = self.json_args.get("username")
            password = self.json_args.get("password")
            user = self.dbUtil.select_one("select * from blog_user where username = %s", (username,))
            if not user:
                return self.my_write_error({"detail": "用户名错误！"},400)
            if user["is_active"] == False: 
                return self.my_write_error({"detail": "未完成用户验证！"}, 400)  
            passwd = encrypt(password)
            if passwd != user["password"]:
                return self.my_write_error({"detail": "密码错误。"}, 400)
            last_login = datetime.utcnow()
            self.dbUtil.update_operation("update blog_user set last_login=%s where username=%s", (last_login, username))
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 400)

        token = jwt_encode({"username": username, "id": user["id"], "is_superuser": True})       
        resp = {
            "expire_days": config.JWT_EXPIRATION_DAYS, 
            "token": token,
            "user": {"id":           user["id"], 
                     "username":     username, 
                     "last_login":   last_login.strftime('%Y-%m-%d %H:%M:%S'), 
                     "email":        user["email"],
                     "avatar":       user["avatar"],
                     "nickname":     user["nickname"],
                     "is_active":    True if user["is_active"]==1 else False, 
                     "is_superuser": True if user["is_superuser"]==1 else False,
                     "created_at":   user["created_at"].strftime('%Y-%m-%d %H:%M:%S') if user["created_at"]!=None else ""}
        }
        timestamp = datetime.now().timestamp()
        self.set_cookie(config.JWT_AUTH_COOKIE, token, expires = timestamp + config.JWT_EXPIRATION_DAYS*24*3600,expires_days=config.JWT_EXPIRATION_DAYS)
        self.write(resp)

class PasswordHandler(BaseHandler):
    def put(self):
        try:
            username = self.json_args.get("username")
            user = self.dbUtil.select_one("select * from blog_user where username = %s", (username,))
            if not user:
                return self.my_write_error({"detail": "用户名错误"}, 500)
            if user["is_active"] == False: 
                return self.my_write_error({"detail": "未完成用户验证！"}, 400)  
         
            password = get_random_password()
            send_mail(subject="您在博客FlaskBlog上的新密码",
                      message="""HI, 您的新密码:\n{password}""".format(password=password),
                      recipient_list=[user["email"]])
                    
            password = encrypt(password)
            self.dbUtil.update_operation("update blog_user set password=%s where username=%s", (password, username))
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)            
        
        self.write({'detail': 'Send New email failed, Please check your email address'})

    def post(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user:
                return
            user_id = curr_user["id"]
            user = self.dbUtil.select_one("select password,is_active from blog_user where id = %s", (user_id,))
            if not user:
                return self.my_write_error({"detail": '用户不存在！'}, 400)              
            
            password = self.json_args.get("password")
            new_password = self.json_args.get("new_password")
            if not user:
                return self.my_write_error({"detail": "用户名错误！"},400)
            if user["is_active"] == False: 
                return self.my_write_error({"detail": "未完成用户验证！"}, 400)  
            passwd = encrypt(password)
            if passwd != user["password"]:
                return self.my_write_error({"detail": "密码错误。"}, 400)
            new_passwd = encrypt(new_password)
            self.dbUtil.update_operation("update blog_user set password=%s where id=%s", (new_passwd, user_id))
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 400)
            
        return self.write({"detail": "修改密码成功"})

class GetConstantHandler(BaseHandler):
    def get(self):
        self.write("ok")

class UploadImageHandler(BaseHandler):
    def post(self, path):
        files = self.request.files
        img_files = files.get('file')
        if img_files:
            full_file_path, file_path = get_upload_file_path(path,img_files[0]["filename"])
            img_file = img_files[0]["body"]
            file = open(full_file_path, 'wb+')
            file.write(img_file)
            file.close()
        return self.write({'url': file_path})
            
class AccountResultHandler(BaseHandler):
    def get(self):
        try:
            sign_type  = self.get_query_argument("type", None)
            user_id    = self.get_query_argument("id", None)
            sign       = self.get_query_argument("sign", None)
            if sign_type and sign_type == 'validation':
                user = self.dbUtil.select_one("select * from blog_user where id = %s", (int(user_id),))
                if user and user["is_active"]:
                    return self.write("已经验证成功，请登录。")
                c_sign = get_sha256(get_sha256(config.SECRET_KEY + str(user["id"])))
                if sign != c_sign:
                    return self.write("Verify Err. 验证失败! ")
                self.dbUtil.update_operation("update blog_user set is_active = %s where id = %s", (1, user["id"]))
                return self.write("<h3>Verify OK.验证成功。恭喜您已经成功的完成邮箱验证，您现在可以使用您的账号来登录本站!</h3>")
            else:
                return self.write("Verify OK.验证成功。")
        except Exception as ex:
            print("ex,",ex)
            return self.write("内部错误。")
       