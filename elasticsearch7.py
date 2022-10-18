from elasticsearch import Elasticsearch
import config
from constants import Constant

esClient = Elasticsearch(config.ELASTICSEARCH_HOST)

setmap = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            "id": {
                "type": "integer"
            },
            "title": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "excerpt": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "keyword": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "markdown": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "catalog_info": {
                "properties": {
                    "name": {
                        "search_analyzer": "ik_smart",
                        "analyzer": "ik_smart",
                        "type": "text"
                    },
                    "id": {
                        "type": "integer"
                    }
                }
            },
            "status": {
                "search_analyzer": "ik_smart",
                "analyzer": "ik_smart",
                "type": "text"
            },
            "views": {
                "type": "integer"
            },
            "comments": {
                "type": "integer"
            },
            "likes": {
                "type": "integer"
            },
            "tags_info": {
                "properties": {
                    "name": {
                        "search_analyzer": "ik_smart",
                        "analyzer": "ik_smart",
                        "type": "text"
                    },
                    "id": {
                        "type": "integer"
                    }
                }
            }
        }
    }
}

def ESCreateIndex(dbUtil):
    try:
        if esClient.indices.exists(index=config.ELASTICSEARCH_INDEX) is True:
            print("index exist")
            esClient.indices.delete(index=config.ELASTICSEARCH_INDEX)

        ret = esClient.indices.create(
            index = config.ELASTICSEARCH_INDEX,
            body = setmap)
    except Exception as ex:
        print("ex,", ex)
        return
    
    page      = 1;
    page_size = 10;
    article_total = dbUtil.select_one("select count(*) as total from blog_article order by id asc")
    total = article_total["total"] 
    try:    
        while total > 0: 
            articles = dbUtil.select_many("select * from blog_article order by id asc limit %s offset %s",
                                           (page_size,(page - 1) * page_size))
            
            page += 1
            total -= len(articles)
            print(total)
        
            catalog_infos = {}
            tag_infos = {}
            for article in articles:
                catalog_info = dbUtil.select_one("select * from blog_catalog where id =%s",(article["catalog_id"],))
                catalog_infos[article["id"]] = {"id":article["catalog_id"],"name": catalog_info["name"] if catalog_info else ""}
                tag_info = dbUtil.select_many("select * from blog_tag a, article_tag b where a.id = b.tag_id and b.article_id=%s",(article["id"],))
                tag_infos[article["id"]] = tag_info

            for article in articles:
                body = {
                    "id":           article["id"],
                    "title":        article["title"],
                    "excerpt":      article["excerpt"],
                    "keyword":      article["keyword"],
                    "markdown":     article["markdown"],
                    "status":       article["status"],
                    "tags_info":    [{"id": tag["id"],"name": tag["name"]} 
                                      for tag in tag_infos.get(article["id"], [])],
                    "catalog_info": catalog_infos.get(article["id"], {}),
                    "views":        article["views"],
                    "comments":     article["comments"],
                    "likes":        article["likes"]
                }
                ret = esClient.index(
                    index = config.ELASTICSEARCH_INDEX, 
                    id = article["id"],
                    body = body)
    except Exception as ex:
        print('ex=',ex)


def ESUpdateIndex(dbUtil,article):
    if config.ELASTICSEARCH_ON==False:
        return

    try:
        catalog_info = dbUtil.select_one("select * from blog_catalog where id =%s",(article["catalog_id"],))
        catalog_infos = {"id":article["catalog_id"],"name": catalog_info["name"] if catalog_info else ""}
        tags_info = dbUtil.select_many("select * from blog_tag a, article_tag b where a.id = b.tag_id and b.article_id=%s",(article["id"],))
            
        body = {
            "id":           article["id"],
            "title":        article["title"],
            "excerpt":      article["excerpt"],
            "keyword":      article["keyword"],
            "markdown":     article["markdown"],
            "status":       article["status"],
            "tags_info":    [{"id": tag["id"],"name": tag["name"]} 
                            for tag in tags_info],
            "catalog_info": catalog_infos,
            "views":        article["views"],
            "comments":     article["comments"],
            "likes":        article["likes"]
        }
        ret = esClient.index(
            index   = config.ELASTICSEARCH_INDEX, 
            refresh = True,
            id      = article["id"],
            body    = body )
    except Exception as ex:
        print('ex=',ex)


def ESSearchIndex(page, page_size, search_text):
    if config.ELASTICSEARCH_ON==False:
        return { "count": 0, "results": [] }
    
    try:
        ret = esClient.search(
            index = config.ELASTICSEARCH_INDEX,
            body  = {
                "query": { 
                    "bool": { 
                              "should": [
                                   { "match": { "title":              search_text }}, 
                                   { "match": { "excerpt":            search_text }},
                                   { "match": { "keyword":            search_text }}, 
                                   { "match": { "markdown":           search_text }},
                                   { "match": { "tags_info.name":     search_text }},
                                   { "match": { "catalog_info.name":  search_text }}
                               ],
                               "must" : {
                                    "match" : {
                                        "status": Constant.ARTICLE_STATUS_PUBLISHED
                                    }
                               }
                            }
                }
            },
            from_ = (page - 1) * page_size,
            size = page_size
        )
    except Exception as ex:
        print("ex,",ex)
        return { "count": 0, "results": [] }
        
    articleList = {}
    if ret != None:
        if ret["hits"]:
            articleList = [{ "object": article["_source"] } for article in ret["hits"]["hits"]]
            return { "count": ret["hits"]["total"]["value"], "results": articleList }
  
    return { "count": 0, "results": [] }
