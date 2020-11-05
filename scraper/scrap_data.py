import sqlite3
from sqlite3 import Error
import requests
requests.packages.urllib3.disable_warnings() #Disable ssl warnings
import time

# -------------------------------------------------------------------------------------
def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    
    return conn

def add_occupancy(conn, data):
    ts = time.gmtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", ts)
    sql = ''' INSERT INTO occupancy(centre_id,currentVisitors,maxVisitors,timestamp)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()
    
    return 


# request the current occupancy
def request_occupancy(centres):
    ts = time.gmtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", ts)
    conn = create_connection(r"../database/centre_occupation.db")
    for centre in centres:
        url = 'https://blfa-api.migros.ch/fp/api/center/' + str(centre) + '/currentuser/'
        response = requests.get(url, verify=False).json()
        
        current_visit = response['currentVisitors']
        
        if type(current_visit) == int:
            add_occupancy(conn,(centre, current_visit, response['maxVisitors'], timestamp))
        else:
            current_visit = 0
            add_occupancy(conn,(centre, current_visit, response['maxVisitors'], timestamp))

    
    conn.close()
    return 
# --------------------------------------------------------------------------------------


def request_all_centers():
    conn = create_connection(r"../database/centre_occupation.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM centres")
    rows = cur.fetchall()
    conn.close()

    centre_ids = [row[0] for row in rows]
    print("Requesting centre occupancy")
    request_occupancy(centre_ids)
    
    print("Waiting 15 Minutes")
    time.sleep(60*15)

    
while True:
    request_all_centers()
