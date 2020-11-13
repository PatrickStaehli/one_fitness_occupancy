from flask import Flask, redirect, url_for, render_template, request, jsonify
from flask_cors import CORS, cross_origin
import cv2 as cv
import sqlite3
import numpy as np
import pandas as pd
from querry_data import create_connection
import datetime
import time

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['JSON_SORT_KEYS'] = False

CORS(app, support_credentials=True)


color_red = [231, 76, 60]
color_orange = [255,69,0]
color_green = [50,205,50]


path_to_database = "../database/centre_occupation.db"



def roundTime(dt=None, roundTo=60):
    """Round a datetime object to any time lapse in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None : dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds+roundTo/2) // roundTo * roundTo
    return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)


def query_data(database, sql_statement):
        conn = create_connection(database)
        cur = conn.cursor()
        cur.execute(sql_statement )
        query_result = cur.fetchall()
        conn.close()
        return query_result



@app.route("/")
def home():
        return render_template("index.html")


@app.route("/api/one_training/occupancy", methods=['GET'])
def api_one_occupancy():
        '''Returns the history of the occupancy and max occupancy for the requested center_id in a json format
        '''
        
        # Read the get argument

        centre_id = request.args.get('centre_id')

        # Query the centre name for the specific centre id 
        centre_prop = query_data(path_to_database, "SELECT * FROM centres WHERE centre_id = " + str(centre_id) ) # Returns (centre_id, centre_name)
        centre_name = centre_prop[0][1]

        # Query the history of the occupancy for the specific centre
        # Request only the last day  %H:%M:%S
        ts = datetime.date.today() - datetime.timedelta(days=30)
        start_time = ts.strftime("%Y-%m-%d")
        
        # NEW: 
        query = "SELECT * FROM occupancy WHERE centre_id = " + str(centre_id) + " AND timestamp >= '" + start_time + "' AND maxVisitors > 0 ORDER BY id"
        conn = sqlite3.connect(path_to_database)

        # Create pandas dataframe
        occupancy_df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert timestamp to datetime and gmt+1
        occupancy_df['timestamp']= pd.to_datetime(occupancy_df['timestamp']) + datetime.timedelta(hours=1)
        occupancy_df['timestamp_round_time'] = pd.to_datetime(occupancy_df['timestamp'], format='%H:%M').dt.round('15min').dt.time
        # Add Weekday column
        occupancy_df['weekday'] = [ts.weekday() for ind, ts in enumerate(occupancy_df['timestamp'])]
        
        weekday = datetime.datetime.today().weekday()
        # Group by weekday
        occupancy_df_weekday = occupancy_df[occupancy_df['weekday'] == weekday]
        
        occupancy_df_grouped_by_time = occupancy_df_weekday.groupby(['timestamp_round_time'])['currentVisitors'].describe()
        occupancy_df_grouped_by_time['std'] = occupancy_df_grouped_by_time['std'].fillna(0)
        occupancy_mean = occupancy_df_grouped_by_time['mean'].to_numpy()
        occupancy_std  = occupancy_df_grouped_by_time['std'].to_numpy()
        
        # old:
        # centre_occupancy = query_data(path_to_database, "SELECT * FROM occupancy WHERE centre_id = " + str(centre_id) + " AND timestamp >= '" + start_time + "' AND maxVisitors > 0 ORDER BY id") # Returns (id, centre_id, currentVisitors, maxVisitors, timestamp)
        centre_occupancy = query_data(path_to_database, query)
        
        
        
        
        # Extract the history of the actual occupancy 
        # occupancy = [ind[2] for ind in centre_occupancy]
        
        # End OLD
        
        
        # Extract the history of the maximum occupancy
        max_occupancy = occupancy_df_weekday.maxVisitors.to_numpy()
        
        
        # Generate labels
        # For each entry, the label looks as 07:15;Samstag.        
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        occupancy_df_weekday['timestamp_round_time'] = occupancy_df_weekday['timestamp_round_time'].astype('str')
        weekdays_list = occupancy_df_weekday['weekday'].tolist()
        round_times_list = occupancy_df_weekday['timestamp_round_time'].tolist()
        
        #_time = [roundTime(datetime.datetime.strptime(ind[4], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=1),15*60) for ind in centre_occupancy]
        #weekday = [datetime.datetime.strptime(ind[4], "%Y-%m-%d %H:%M:%S").weekday() for ind in centre_occupancy]
        #labels = [str(_time[i].strftime('%H:%M')) + ";" + weekdays[weekday[i]] for i in range(len(_time))]
        labels = [round_times_list[i][0:5] + ";" + weekdays[weekdays_list[i]] for i in range(len(weekdays_list))]
        
        # Generate json structure
        occupancy_history = {labels[i]: {'occupancy': occupancy_mean[i], 'occupancy_std': occupancy_std[i], 'max_occupancy': int(max_occupancy[i])} for i in range(len(occupancy_mean))}
        centre_properties  = {'centre_properties': {'centre_id': centre_id, 'name': centre_name}, 'occupancy_history': occupancy_history}
        response = jsonify(centre_properties)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


@app.route("/one_occupancy")
def one_occupancy():
        '''
        Renders the one_occupancy.html template. The most current occupancy is requested and past to the template where
        it is visualized via doughnut charts for each centre. 
        '''
        
        
        # Request all the center names
        centres = query_data(path_to_database, "SELECT * FROM centres") # Returns (centre_id, centre_name)
        centre_ids = [centre[0] for centre in centres]
        centre_names = [centre[1] for centre in centres]
        
        
        # Request the most current centre occupancy for each centre
        current_occupancy = []
        current_max_occupancy = []
        for i, centre_id in enumerate(centre_ids):
                centre_occupancy = query_data(path_to_database, "SELECT * FROM occupancy WHERE centre_id = " + str(centre_id) + " AND timestamp >=  '2020-10-31' AND timestamp IN (SELECT max(timestamp) FROM occupancy)") # Returns (id, centre_id, currentVisitors, maxVisitors, timestamp)
                if not centre_occupancy:
                    print(str(centre_id) + ": Data not available ")
                    current_occupancy.append(0)
                    current_max_occupancy.append(0)
                else:
                    current_occupancy.append(centre_occupancy[0][2])
                    current_max_occupancy.append(centre_occupancy[0][3])
        
        # Create the labels for the doughnut charts (e.g. 10%) 
        # If current_max_occupancy is 0, this means that the centre is closed.
        current_occupancy_percent = []
        for i in range(len(current_max_occupancy)):     
            if current_max_occupancy[i] == 0:
                current_occupancy_percent.append('--')
            else:
                current_occupancy_percent.append(str(int(np.round(current_occupancy[i]/current_max_occupancy[i]*100))) + '%')
                
        # Define the color for the donught plot 
        # Low (< 15%) occupancy -> Green, Middle (< 20) -> orange, High (>=20) red
        current_color = []
        for i in range(len(current_occupancy)):
            if current_max_occupancy[i] > 0:
                if current_occupancy[i]/current_max_occupancy[i] < 0.4:
                    current_color.append(color_green)
                elif current_occupancy[i]/current_max_occupancy[i] < 0.8:
                    current_color.append(color_orange)
                else:
                    current_color.append(color_red)
            else:  
                current_color.append(color_red)

        
        # Render the html template
        return render_template("one_occupancy.html", len = len(centre_names), centre_ids = centre_ids, centres = centre_names, current_occupancy_percent = current_occupancy_percent, current_occupancy = current_occupancy, current_max_occupancy = current_max_occupancy, current_color=current_color)


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

if __name__ == "__main__":
        app.run(debug=True)
        

