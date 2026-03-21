import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='sql@4545', database='hostel_db')
c = conn.cursor(dictionary=True)

for table in ['warden', 'hostel', 'room']:
    c.execute(f"DESCRIBE {table}")
    print(f"--- {table} ---")
    rows = c.fetchall()
    for r in rows:
        print(r['Field'])
