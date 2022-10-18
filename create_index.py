from elasticsearch7  import ESCreateIndex
from utils.MySQLUtil import  MySQLdbUtil
import config

if __name__ == "__main__":
    dbUtil = MySQLdbUtil(**config.mysql_options)
    ESCreateIndex(dbUtil)
    print("created index")