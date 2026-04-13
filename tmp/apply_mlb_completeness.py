import psycopg2, pathlib, sys
sql_path = pathlib.Path('/home/cbwinslow/workspace/retrosheet/sql/150_mlb_data_completeness.sql')
sql = sql_path.read_text()
try:
    conn = psycopg2.connect(dbname='retrosheet', user='postgres', host='localhost', port=5432)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print('Migration applied')
except Exception as e:
    print('Error:', e)
