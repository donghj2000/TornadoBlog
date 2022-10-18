#!/usr/bin/env python  
#coding:utf-8 

import logging
import MySQLdb

from MySQLdb import cursors


class MySQLdbUtil(object):
    def __init__(self, host, user, password, database, port,charset, use_unicode):
        self.conn = MySQLdb.connect(host=host, user=user, password=password, database=database, port=port,charset=charset, use_unicode=use_unicode)
        self.cursor = self.conn.cursor(cursors.DictCursor)

    def select_one(self, *sql):
        try:
            print(sql)
            self.cursor.execute(*sql)
            self.conn.commit()
            data = self.cursor.fetchone()
            return data
        except Exception as e:
            logging.error(e)
            self.conn.rollback()

    def select_many(self, *sql):
        try:
            print(sql)
            self.cursor.execute(*sql)
            self.conn.commit()
            data = self.cursor.fetchall()
            return data
        except Exception as e:
            print("e,", e)
            logging.error(e)
            self.conn.rollback()
    def execute_operation(self, *sql):
        try:
            print(sql)
            count = self.cursor.execute(*sql)
            self.conn.commit()
            return count
        except Exception as e:
            print("e,", e)
            logging.error(e)
            self.conn.rollback()

    def delete_operation(self, *sql):
        self.execute_operation(*sql)

    def update_operation(self, *sql):
        self.execute_operation(*sql)

    def insert_operation(self, *sql):
        self.execute_operation(*sql)
