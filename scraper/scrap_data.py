import requests
from db_lib import SQLiteConnector
requests.packages.urllib3.disable_warnings() #Disable ssl warnings
import time


def add_occupancy_to_database(conn, data):
    '''
    Inserts a new row with occupancy data into the occupancy table
    
    :param  db_file: sqlite connector Connector to the database
            data: tuple in form of (centre_id, current_visitors, current_max_visitors, timestamp)
    '''
    
    sql = ''' INSERT INTO occupancy(centre_id,currentVisitors,maxVisitors,timestamp)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()
    
    return 


def request_occupancy(centres):
    '''
    Requests the current centre occupation via get request from the url:
    'https://blfa-api.migros.ch/fp/api/center/<center_id>/currentuser/' and 
    inserts the data into the database.
    
    :param: centres: List of all centre id'save
    
    :return: List of request status for each centre. 200 means a successful request.
    '''
    
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
                add_occupancy_to_database(cnxn.connection,(centre, current_visit, response['maxVisitors'], timestamp))
            else:
                current_visit = 0
                add_occupancy_to_database(cnxn.connection,(centre, current_visit, response['maxVisitors'], timestamp))
        else:
            centre_status[centre] = response.status_code # save the status code
            
    cnxn.close_connection()
    
    return centre_status


def request_all_centers():
    '''
    Requests the centre occupancy for all centres that are stored in the
    centre_occupation - centres table.
    The request status code is written to the scraper_output.txt file.
    '''
    cnxn = SQLiteConnector(r"../database/centre_occupation.db")
    
    cur = cnxn.connection.cursor()
    cur.execute("SELECT * FROM centres")
    rows = cur.fetchall()
    cnxn.close_connection()

    centre_ids = [row[0] for row in rows]
    request_center_status = request_occupancy(centre_ids)
    
    ts = time.gmtime()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", ts)

    with open("scraper_output.txt", "a") as f:
        f.write(str(timestamp) + "\n")
        f.write("Request status: \n")
        f.write(str(request_center_status))
        f.write("\n----------------------------------------------------------------------------------------------------------------------------------------------\n \n")
        f.close()


# The occupancy data is requested every 15 minutes
while True:
    request_all_centers()
    time.sleep(60*15)