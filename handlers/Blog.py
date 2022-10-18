#coding:utf-8
import logging
import hashlib
import config
import json
from tornado.web import RequestHandler
from .BaseHandler import BaseHandler
from constants import Constant
from elasticsearch7   import ESUpdateIndex, ESSearchIndex


# 递归获取父节点 id
ancestorIds = []
def get_ancestors(db, parent_id):
    if parent_id != 0 and parent_id  != None:
        ancestorIds.insert(0, parent_id)
        try:
            ret = db.select_one("select parent_id from blog_catalog where id = %s", (parent_id,))
            if ret:
                parent_id_tmp = ret["parent_id"]
                get_ancestors(db, parent_id_tmp)
            else:
                return ancestorIds
        except Exception as ex:
            print("ex,",ex)
            return ancestorIds
    else:
        return ancestorIds
        
# 递归获取子节点 id
descendantsIds = []
def get_descendants(db, catalog_id):
    descendantsIds.append(catalog_id)
    try:
        catalogs = db.select_many("select id from blog_catalog where parent_id = %s", (catalog_id, ))
        if len(catalogs) != 0:
            for cata in catalogs:
                get_descendants(db, cata["id"])
        else:
            return descendantsIds
    except Exception as ex:
        print("ex,", ex)
        return descendantsIds

class AriticleListHandler(BaseHandler):
    def get(self):
        try:
            status    = self.get_query_argument("status",    None)
            search    = self.get_query_argument("search",    None)
            tag       = self.get_query_argument("tag",       None)
            catalog   = self.get_query_argument("catalog",   None)
            page      = self.get_query_argument("page",      "1")
            page_size = self.get_query_argument("page_size", "10")
 
            articles = None
            sql = "select * from blog_article "
            params = []
            sql_where = []    
            if status != None and status != "":
                sql_where.append("status = %s ")
                params.append(status)  
            if search != None and search != "":
                sql_where.append("locate(%s,title)!=0")
                params.append(search)
            if tag != None:
                article_tags = self.dbUtil.select_many("select * from article_tag where tag_id = %s", (int(tag),))
                if article_tags:
                    sql_where.append("id in %s ")
                    article_ids = []
                    for art_tag in article_tags:
                        article_ids.append(art_tag["article_id"])
                    params.append(article_ids)
            if catalog != None:
                #搜索子类型
                global descendantsIds
                descendantsIds = []
                get_descendants(self.dbUtil, int(catalog))
                sql_where.append("catalog_id in %s ")
                params.append(descendantsIds)
                    
            if len(sql_where)!=0:
                sql += "where "
                sql += " and ".join(sql_where)
            sql += " order by id asc "
            sql += " limit %s offset %s"
            params.append(int(page_size))
            params.append((int(page) - 1) * int(page_size))
            articles = self.dbUtil.select_many(sql, params) 
      
            catalog_infos = {}
            tag_infos = {}
            for article in articles:
                global ancestorIds
                ancestorIds = []
                get_ancestors(self.dbUtil, article["catalog_id"])
                catalog_info = self.dbUtil.select_one("select * from blog_catalog where id =%s",(article["catalog_id"],))
                catalog_infos[article["id"]] = {"id":article["catalog_id"],"name": catalog_info["name"] if catalog_info else "","parents": ancestorIds}
                tag_info = self.dbUtil.select_many("select * from blog_tag a, article_tag b where a.id = b.tag_id and b.article_id=%s",(article["id"],))
                tag_infos[article["id"]] = tag_info

            ret = {}
            ret["count"] = len(articles)
            ret["results"] = [{
                    "id":           article["id"],
                    "title":        article["title"],
                    "excerpt":      article["excerpt"],
                    "cover":        article["cover"],
                    "status":       article["status"],
                    "created_at":   article["created_at"].strftime('%Y-%m-%d %H:%M:%S') if article["created_at"]!=None else "",
                    "modified_at":  article["modified_at"].strftime('%Y-%m-%d %H:%M:%S') if article["modified_at"]!=None else "",
                    "tags_info":    [{"id": tag["id"], "name": tag["name"], 
                                     "created_at": tag["created_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["created_at"]!=None else "",
                                     "modified_at":tag["modified_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["modified_at"]!=None else ""
                                     } for tag in tag_infos.get(article["id"], [])],
                    "catalog_info": catalog_infos.get(article["id"], {}),
                    "views":        article["views"],
                    "comments":     article["comments"],
                    "words":        article["words"],
                    "likes":        article["likes"] 
            } for article in articles] 
            return self.write(ret)
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error(dict(detail = "内部错误!"), 500)
        
    def post(self):
        curr_user = self.get_current_user()
        if not curr_user or not curr_user["is_superuser"]:
            return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
        try:
            title    = self.json_args.get("title")
            cover    = self.json_args.get("cover", "")
            excerpt  = self.json_args.get("excerpt", "")
            keyword  = self.json_args.get("keyword", "")
            markdown = self.json_args.get("markdown", "")
            tags     = self.json_args.get("tags", [])
            catalog  = self.json_args.get("catalog", 0)

            ret = self.dbUtil.select_one("select * from blog_article where title = %s", (title,))
            if ret:
                return self.my_write_error({"detail": "标题已经存在！"}, 500)
            
            article = self.dbUtil.insert_operation(
                "insert into blog_article(title,cover,excerpt,keyword,markdown,catalog_id,author_id,creator,modifier) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (title,cover,excerpt,keyword,markdown,catalog,curr_user.get("id", 1),
                 curr_user.get("id", 1), curr_user.get("id", 1))) 
                                    
            if len(tags) != 0:
                article = self.dbUtil.select_one("select * from blog_article where title=%s",(title,))
                sql = "insert into article_tag values"
                params_str = []
                params_val = []
                for tag_id in tags:
                    params_str.append("(%s,%s)")
                    params_val.append(article["id"])
                    params_val.append(tag_id)
                sql += ",".join(params_str)    
                self.dbUtil.insert_operation(sql,params_val)

            ESUpdateIndex(self.dbUtil, article)
            return self.my_write_error({"detail": "保存文章成功！"}, 201)   
        except Exception as ex:
            print('ex,',ex)
            return self.my_write_error({"detail": "内部错误！"}, 500)
        
class AriticleHandler(BaseHandler):
    def get(self, article_id):
        try:
            article = self.dbUtil.select_one("select * from blog_article where id = %s", (int(article_id),)) 
            global ancestorIds
            ancestorIds = []
            get_ancestors(self.dbUtil, article["catalog_id"])
            catalog_info = self.dbUtil.select_one("select * from blog_catalog where id =%s",(article["catalog_id"],))
            catalog_infos = {"id":article["catalog_id"],"name": catalog_info["name"] if catalog_info else "","parents": ancestorIds}
            tag_infos = self.dbUtil.select_many("select * from blog_tag a, article_tag b where a.id = b.tag_id and b.article_id=%s",(article["id"],))
    
            ret = {
                    "id":           article["id"],
                    "title":        article["title"],
                    "excerpt":      article["excerpt"],
                    "keyword":      article["keyword"],
                    "cover":        article["cover"],
                    "markdown":     article["markdown"],
                    "status":       article["status"],
                    "created_at":   article["created_at"].strftime('%Y-%m-%d %H:%M:%S') if article["created_at"]!=None else "",
                    "modified_at":  article["modified_at"].strftime('%Y-%m-%d %H:%M:%S') if article["modified_at"]!=None else "",
                    "tags_info":    [{"id": tag["id"], "name": tag["name"], 
                                     "created_at": tag["created_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["created_at"]!=None else "",
                                     "modified_at":tag["modified_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["modified_at"]!=None else ""
                                     } for tag in tag_infos],
                    "catalog_info": catalog_infos,
                    "views":        article["views"],
                    "comments":     article["comments"],
                    "words":        article["words"],
                    "likes":        article["likes"] 
            } 
            self.dbUtil.update_operation("update blog_article set views = views+1 where id=%s", (article["id"],))
            return self.write(ret)
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error(dict(detail = "内部错误!"), 500)
    
    def put(self, article_id):
        curr_user = self.get_current_user()
        if not curr_user or not curr_user["is_superuser"]:
            return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
        try:
            title    = self.json_args.get("title")
            cover    = self.json_args.get("cover", "")
            excerpt  = self.json_args.get("excerpt", "")
            keyword  = self.json_args.get("keyword", "")
            markdown = self.json_args.get("markdown", "")
            tags     = self.json_args.get("tags", [])
            catalog  = self.json_args.get("catalog", 0)

            self.dbUtil.update_operation("update blog_article set title=%s,cover=%s,excerpt=%s,keyword=%s,markdown=%s,catalog_id=%s where id=%s", 
                                         (title, cover, excerpt, keyword,markdown,catalog,int(article_id)))
            self.dbUtil.delete_operation("delete from article_tag where article_id=%s", (int(article_id),))            
            if len(tags) != 0:
                sql = "insert into article_tag values"
                params_str = []
                params_val = []
                for tag_id in tags:
                    params_str.append("(%s,%s)")
                    params_val.append(int(article_id))
                    params_val.append(tag_id)
                sql += ",".join(params_str)    
                self.dbUtil.insert_operation(sql,params_val)
                
            article = self.dbUtil.select_one("select * from blog_article where id = %s", (int(article_id),))
            ESUpdateIndex(self.dbUtil, article)
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error(dict(detail = "内部错误!"), 500)

    def patch(self, article_id):
        curr_user = self.get_current_user()
        if not curr_user or not curr_user["is_superuser"]:
            return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
        try:
            status = self.json_args.get("status")
            self.dbUtil.update_operation("update blog_article set status=%s where id=%s",(status,article_id))
            article = self.dbUtil.select_one("select * from blog_article where id = %s", (int(article_id),))
            ESUpdateIndex(self.dbUtil, article)
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error(dict(detail = "内部错误!"), 500)
        
class ArchiveListHandler(BaseHandler):
    def get(self):
        page      = self.get_query_argument("page",      "1")
        page_size = self.get_query_argument("page_size", "10")
        try:
            article_total = self.dbUtil.select_one("select count(*) as total from blog_article where status=%s order by id asc",
                                                   (Constant.ARTICLE_STATUS_PUBLISHED,))
            total = article_total["total"]
            page = self.dbUtil.select_many("select * from blog_article where status=%s order by id asc limit %s offset %s",
                                          (Constant.ARTICLE_STATUS_PUBLISHED,int(page_size),(int(page) - 1) * int(page_size)))
        except Exception as ex:
            print("ex,", ex)
            return self.my_write_error({"detail": "内部错误"}, 500)
    
        if page is not None:
            ret = {
                "count": total,
                "next": None,
                "previous": None,
                "results": [] }
            if total != 0:
                years = {}
                for article in page:
                    year = article["created_at"].year
                    articles_year = years.get(year)
                    if not articles_year:
                        articles_year = []
                        years[year] = articles_year
                    
                    articles_year.append({
                                          "id":         article["id"],
                                          "title":      article["title"],
                                          "created_at": article["created_at"].strftime('%Y-%m-%d %H:%M:%S') if article["created_at"]!=None else "" })
                
                for key, value in years.items():
                    ret["results"].append({
                        "year": key,
                        "list": value})
                ret["results"].sort(key=lambda i:i["year"], reverse=True)

        return self.write(ret)
        
def getReplies(db,replies):
    comment_replies = []
    if len(replies)==0:
        return []
    for reply in replies:
        user_rep = db.select_one("select * from blog_user where id=%s",(reply["user_id"],))
        reply_replies = db.select_many("select * from blog_comment where reply_id=%s", (reply["id"],))
        if user_rep != None:
            comment_replies.append({
                "id":              reply["id"],
                "content":         reply["content"],
                "user_info":       {
                                       "id":     user_rep["id"],
                                       "name":   user_rep["nickname"] or user_rep["username"],
                                       "avatar": user_rep["avatar"],   
                                       "role":   "Admin" if user_rep["is_superuser"]==1 else "" 
                                   },
                "created_at":      reply["created_at"].strftime('%Y-%m-%d %H:%M:%S') if reply["created_at"]!=None else "",
                "comment_replies": getReplies(db,reply_replies) })
    return comment_replies 
    
class CommentListHandler(BaseHandler):
    def get(self):
        user_id    = self.get_query_argument("user",      None)
        search     = self.get_query_argument("search",    None)
        article_id = self.get_query_argument("article",   None)
        page       = self.get_query_argument("page",      None)
        page_size  = self.get_query_argument("page_size", None)
        
        try:
            sql = "select * from blog_comment "
            params = []        
            sql_where = []    
            if user_id != None and user_id != "":
                sql_where.append("user_id = %s ")
                params.append(int(user_id))  
            if search != None and search != "":
                sql_where.append("locate(%s,content)!=0")
                params.append(search)
            if article_id != None and article_id != "":
                sql_where.append("article_id = %s ")
                params.append(int(article_id))
            if len(sql_where)!=0:
                sql += "where "
                sql += " and ".join(sql_where)
            sql += " order by id asc "
            if page != None and page != "":
                sql += " limit %s offset %s"
                params.append(int(page_size))
                params.append((int(page) - 1) * int(page_size))
            comments = self.dbUtil.select_many(sql, params) 
        except Exception as ex:
            print("ex,", ex)
            return self.my_write_error({"detail": "内部错误"}, 500)
        
        ret = {};
        ret["count"] = len(comments)
        ret["results"] = []
        for comment in comments:
            user = self.dbUtil.select_one("select * from blog_user where id = %s",(comment["user_id"],))
            user_info = {
                "id":    user["id"],
                "name":  user["nickname"] or user["username"],
                "avatar":user["avatar"],
                "role"  :"Admin" if user["is_superuser"]==1 else ""
            } 
            article = self.dbUtil.select_one("select id,title from blog_article where id=%s", (comment["article_id"],))
            article_info = {
                "id":    article["id"], 
                "title": article["title"] }

            replies = self.dbUtil.select_many("select * from blog_comment where reply_id=%s", (comment["id"],))
            comment_replies = getReplies(self.dbUtil,replies)
            ret["results"].append({
                "id":              comment["id"],
                "user":            comment["user_id"],
                "user_info":       user_info,
                "article":         comment["article_id"], 
                "article_info":    article_info,
                "created_at":      comment["created_at"].strftime('%Y-%m-%d %H:%M:%S') if comment["created_at"]!=None else "", 
                "reply":           comment["reply_id"], 
                "content":         comment["content"],
                "comment_replies": comment_replies })
        return self.write(ret)
        
    def post(self):
        curr_user = self.get_current_user()
        if not curr_user:
            return self.my_write_error(dict(detail = "没有登陆!"), 400)
        try:
            article_id = self.json_args.get("article")
            user_id    = self.json_args.get("user")
            reply_id   = self.json_args.get("reply")
            content    = self.json_args.get("content")

            sql = "insert into blog_comment(article_id, user_id, content,creator,modifier"
            params = [article_id, user_id, content,user_id,user_id]
            if reply_id != None:
                sql += ",reply_id"
                params.append(reply_id)
            sql += ") values(%s,%s,%s,%s,%s"
            if reply_id != None:
                sql += ",%s"
            sql += ")"
            
            self.dbUtil.insert_operation(sql, params)
            self.dbUtil.update_operation("update blog_article set comments = comments+1 where id=%s", (article_id,))
            return self.my_write_error({"detail": "评论成功！"}, 201) 
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
        
class LikeListHandler(BaseHandler):   
    def post(self):
        curr_user = self.get_current_user()
        if not curr_user:
            return self.my_write_error(dict(detail = "没有登陆!"), 400)
        try:
            article_id = self.json_args.get("article")
            user_id    = self.json_args.get("user")

            sql = "insert into blog_like(article_id, user_id, creator,modifier) values(%s,%s,%s,%s)"
            params = [article_id, user_id, user_id, user_id]     
            self.dbUtil.insert_operation(sql, params)
            self.dbUtil.update_operation("update blog_article set likes = likes+1 where id=%s", (article_id,))
            return self.my_write_error({"detail": "点赞成功！"}, 201) 
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

class MessageListHandler(BaseHandler):
    def get(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
        
            search    = self.get_query_argument("search", None)
            page      = self.get_query_argument("page", "1")
            page_size = self.get_query_argument("page_size", "10")
            sql = "select * from blog_message "        
            params = []
            if search != None and search != "":
                sql += "where locate(%s,name)!=0 or locate(%s,email)!=0 or locate(%s,phone)!=0 or locate(%s,content)!=0 "
                params = [search,search,search,search]
            sql += "limit %s offset %s"   
            params.append(int(page_size))
            params.append((int(page) - 1) * int(page_size))
            msgs = self.dbUtil.select_many(sql, params)
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
       
        ret = {}
        ret["count"] = len(msgs)
        ret["results"] = [{
            "id":         msg["id"],
            "email":      msg["email"],
            "content":    msg["content"],
            "phone":      msg["phone"],
            "name":       msg["name"],
            "created_at": msg["created_at"].strftime('%Y-%m-%d %H:%M:%S') if msg["created_at"]!=None else "" } for msg in msgs]
        return self.write(ret)
        
    def post(self):
        try:
            email   = self.json_args.get("email")
            content = self.json_args.get("content")
            phone   = self.json_args.get("phone")
            name    = self.json_args.get("name")
            
            sql = "insert into blog_message(email, content, phone, name) values(%s,%s,%s,%s)"
            params = [email, content, phone, name]
            self.dbUtil.insert_operation(sql, params)
            return self.my_write_error({"detail": "留言成功！"}, 201) 
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
        
class TagListHandler(BaseHandler):
    def get(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)

            name      = self.get_query_argument("name", None)
            page      = self.get_query_argument("page", "1")
            page_size = self.get_query_argument("page_size", "10")
            sql = "select * from blog_tag "        
            params = []
            if name != None and name != "":
                sql += "where locate(%s,name)!=0 "
                params.append(name)
            sql += "limit %s offset %s"   
            params.append(int(page_size))
            params.append((int(page) - 1) * int(page_size))
            tags = self.dbUtil.select_many(sql, params)
        except Exception as ex:
            print("ex,", ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

        ret = {}
        ret["count"] = len(tags)
        ret["results"] = [{
            "id":          tag["id"],
            "name":        tag["name"],
            "created_at":  tag["created_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["created_at"]!=None else "",
            "modified_at": tag["modified_at"].strftime('%Y-%m-%d %H:%M:%S') if tag["modified_at"]!=None else "" } for tag in tags]

        return self.write(ret)
        
    def post(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            name   = self.json_args.get("name")
            tag = self.dbUtil.insert_operation("insert into blog_tag(creator,modifier,name) values(%s, %s, %s)", 
                                               (curr_user.get("id", 1), curr_user.get("id", 1), name))
            return self.my_write_error({"detail": "新增标签成功！"}, 201) 
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

class TagHandler(BaseHandler):
    def put(self, tag_id):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            name   = self.json_args.get("name")
            catalog = self.dbUtil.update_operation("update blog_tag set name = %s where id = %s", (name, int(tag_id)))
            return self.write({"detail": "修改标签成功！"})
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

    def delete(self, tag_id): #DeleteTag
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            self.dbUtil.delete_operation("delete from blog_tag where id = %s", (int(tag_id),))             
            return self.write({"detail": "删除标签成功！"})   
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

def is_leaf_node(db, catalog):
    hasDescendants = db.select_many("select id from blog_catalog where parent_id = %s", (catalog["id"],))
    if hasDescendants==None or len(hasDescendants)==0:
        return True
    return False
    
class CatalogListHandler(BaseHandler):        
    def get(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            catas = self.dbUtil.select_many("select * from blog_catalog")
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail", "内部错误!"}, 500)
            
        ret = []
        descendants = []
        for cata in catas:
            if cata["parent_id"] == None:
                root = cata
            else:
                descendants.append(cata)
        root_dict = {
                     "id":        root["id"],  
                     "name":      root["name"],
                     "parent_id": None }
        root_dict['children'] = []
        ret.append(root_dict)
        parent_dict = {root["id"]:root_dict}
        for cls in descendants:
            data = {
                     "id":        cls["id"],  
                     "name":      cls["name"],
                     "parent_id": cls["parent_id"] }
            parent_id = data.get('parent_id')
            parent = parent_dict.get(parent_id)
            parent['children'].append(data) 
            if not is_leaf_node(self.dbUtil, cls) and cls["id"] not in parent_dict:
                data['children'] = []
                parent_dict[cls["id"]] = data
        return self.write(json.dumps(ret))

    def post(self):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)

            name   = self.json_args.get("name")
            parent = self.json_args.get("parent", 0)              
            catalog = self.dbUtil.insert_operation("insert into blog_catalog(creator, modifier, name, parent_id) values(%s, %s, %s, %s) ",
                                                   (curr_user.get("id", 1), curr_user.get("id", 1), name, parent))
            return self.write({"detail": "新增分类成功！"}) 
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

class CatalogHandler(BaseHandler):
    def patch(self, catalog_id):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            name   = self.json_args.get("name")
            catalog = self.dbUtil.update_operation("update blog_catalog set name = %s where id = %s", (name, int(catalog_id)))
            return self.write({"detail": "修改类型成功！"})
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

    def delete(self, catalog_id):
        try:
            curr_user = self.get_current_user()
            if not curr_user or not curr_user["is_superuser"]:
                return self.my_write_error(dict(detail = "没有管理员权限!"), 400)
            self.dbUtil.delete_operation("delete from blog_catalog where id = %s", (int(catalog_id),))             
            return self.write({"detail": "删除类型成功！"})   
        except Exception as ex:
            print("ex,",ex)
            return self.my_write_error({"detail": "内部错误"}, 500)

class NumberListHandler(BaseHandler):
    def get(self):
        sum_article = self.dbUtil.select_one("select sum(views) as sumviews,sum(likes) as sumlikes,sum(comments) as sumcomments from blog_article")
        sum_msg = self.dbUtil.select_one("select count(*) as summsg from blog_message")
        ret = {
            "views":    int(sum_article["sumviews"]),
            "likes":    int(sum_article["sumlikes"]),
            "comments": int(sum_article["sumcomments"]),
            "messages": sum_msg["summsg"]
        }
        return self.write(ret)
                
class TopListHandler(BaseHandler):
    def get(self):
        try:
            articles = self.dbUtil.select_many("select * from blog_article order by views desc limit 10 offset 0")
        except Exception as ex:
            print("ex,", ex)
            return self.my_write_error({"detail": "内部错误"}, 500)
            
        ret = {}
        ret["count"] = len(articles)
        ret["results"] = [{
            "id":     article["id"],
            "title":  article["title"],
            "views":  article["views"],
            "likes":  article["likes"] } for article in articles]
        
        return self.write(ret)

class EsListHandler(BaseHandler):
    def get(self):
        text      = self.get_query_argument("text", None)
        page      = self.get_query_argument("page", "1")
        page_size = self.get_query_argument("page_size", "10")
        ret = ESSearchIndex(int(page), int(page_size), text);
        self.write(ret)
