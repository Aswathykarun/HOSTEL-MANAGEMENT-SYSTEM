import pymysql

def get_mysql_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="hostel_db",
        cursorclass=pymysql.cursors.DictCursor
    )