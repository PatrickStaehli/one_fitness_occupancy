import sqlite3
from sqlite3 import Error
import requests
from db_lib import SQLiteConnector
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
    cnxn = SQLiteConnector(r"../database/centre_occupation.db")
    centre_status = {} #Get response status for each centre. 200 is success
    
    for centre in centres:
        url = 'https://blfa-api.migros.ch/fp/api/center/' + str(centre) + '/currentuser/'
        response = requests.get(url, verify=False)

        if response.status_code == 200: #If the request is successful
            centre_status[centre] = response.status_code # save the status code
            response = response.json() #jsonify the request

            current_visit = response['currentVisitors']
        
            if type(current_visit) == int:
                add_occupancy(cnxn.connection,(centre, current_visit, response['maxVisitors'], timestamp))
            else:
                current_visit = 0
                add_occupancy(cnxn.connection,(centre, current_visit, response['maxVisitors'], timestamp))
        else:
            centre_status[centre] = response.status_code # save the status code
            
    cnxn.close_connection()
    return centre_status
# --------------------------------------------------------------------------------------


def request_all_centers():
    cnxn = SQLiteConnector(r"../database/centre_occupation.db")
    
    cur = cnxn.connection.cursor()
    cur.execute("SELECT * FROM centres")
    rows = cur.fetchall()
    cnxn.close_connection()

    centre_ids = [row[0] for row in rows]
    request_center_status = request_occupancy(centre_ids)
    
    ts = time.gmtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", ts)
    
    print(timestamp)
    print("Request status:")
    print(request_center_status)
    print("----------------------------------------------------------------------------------------------------------------------------------------------\n \n")
    time.sleep(60*15)

    
while True:
    request_all_centers()
