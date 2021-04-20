import sqlite3
from sqlite3 import Error

class SQLiteConnector:
    ''' Creates a sqlite connection to a database
    
    Attributes
    ----------
    db_path : string  Relative path to the database
    connection : sqlite connector Connector to the database
        
    Methods
    -------
    create_connection(path_to_db)   Creates a connection to the database
    close_connection()  Closes the connection to the database
    '''
    
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.connection = self.create_connection(self.path_to_db)
    
    def create_connection(self, path_to_db):
        """ create a database connection to the SQLite database
        specified by db_file
        
        :param db_file: database file
        
        :return: Connection object or None
        """
        conn = None
        try:
            conn = sqlite3.connect(path_to_db)
            return conn
        except Error as e:
            print(e)
        
        return conn
        
    def close_connection(self):
        '''Closes the connection to the database'''
        self.connection.close()
        
        
        
        
        
        
        