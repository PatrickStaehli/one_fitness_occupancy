import sqlite3
from sqlite3 import Error
import numpy as np


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


def querry_data(db_file):
    centre_id = 127

    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute("SELECT * FROM occupancy WHERE centre_id = " + str(centre_id) + " AND timestamp >=  '2020-10-31' ORDER BY id")
    centre_occupancy = cur.fetchall()
    cur.execute("SELECT * FROM centres WHERE centre_id = " + str(centre_id))
    centre_prop = cur.fetchall()
    conn.close()

    values = [ind[2] for ind in centre_occupancy]
    labels = [ind[4][11:16] for ind in centre_occupancy] 
    
    return values, labels