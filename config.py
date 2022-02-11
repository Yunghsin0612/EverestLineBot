DIALECT='mssql'
DRIVER='SQL Server'
USERNAME='root'
PASSWORD='root'
HOST='127.0.0.1'
PORT='3306'
DATABASE='flask0'
#這個連線字串變數名是固定的具體 參考 flask_sqlalchemy 文件 sqlalchemy會自動找到flask配置中的 這個變數
SQLALCHEMY_DATABASE_URI='{}+{}://{}:{}@{}:{}/{}?charset=utf8'.format(DIALECT,DRIVER,USERNAME,PASSWORD,HOST,PORT,DATABASE)