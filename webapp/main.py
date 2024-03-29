from flask import Flask, redirect, url_for, render_template, request, jsonify
from flask_cors import CORS, cross_origin
import numpy as np
import pandas as pd
import datetime
import time

from db_lib import SQLiteConnector
from opening_hours import opening_hours

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['JSON_SORT_KEYS'] = False

CORS(app, support_credentials=True)

# Define the colors for the doughnut plots
color_red = [231, 76, 60]
color_orange = [255,69,0]
color_green = [50,205,50]

path_to_database = "../database/centre_occupation.db"


@app.route("/one_occupancy/api/one_training/daily_occupancy", methods=['GET'])
def daily_occupancy():
	cnxn = SQLiteConnector(path_to_database)
	df = pd.read_sql('SELECT * FROM occupancy', cnxn.connection)
	centres = cnxn.query_data('SELECT * FROM centres')
	cnxn.close_connection()
	
	occupancy = pd.DataFrame()
	for centre in centres:
		print(centre[0])

		centre_id = centre[0]
		centre_name = centre[1]
		
		# Filter by centre index
		df_centre = df[df['centre_id'] == centre_id]

		# Make datetime
		df_centre['timestamp'] = pd.to_datetime(df['timestamp'])

		# Add day of week
		df_centre['day_of_week'] = df_centre['timestamp'].dt.dayofweek

		# Set timestamp as index
		df_centre_dtindex = df_centre.set_index('timestamp')


		# Filter Opening times
		df_centre_dtindex_openingH = pd.DataFrame()
		for day in range(7):
			df_centre_opening_time_filtered_ = df_centre_dtindex[df_centre_dtindex['day_of_week'] == day].between_time(opening_hours[centre_id][day][0], opening_hours[centre_id][day][1])    
			df_centre_dtindex_openingH = pd.concat([df_centre_dtindex_openingH, df_centre_opening_time_filtered_])


		# Aggregate days
		df_mean_day = df_centre_dtindex_openingH.resample('D', loffset='30Min30s').agg({'currentVisitors': 'mean', 'maxVisitors': 'mean'})
		df_mean_day['centre_id'] =  [centre_id for i in range(len(df_mean_day))]
		df_mean_day['centre_name'] = [centre_name for i in range(len(df_mean_day))]
		# Add to df
		occupancy = pd.concat([occupancy, df_mean_day])
	
	# Add day of week
	occupancy['timestamp'] = occupancy.index
	# Add day of week
	occupancy['day_of_week'] = occupancy['timestamp'].dt.dayofweek
	occupancy.index = range(len(occupancy))

	return(occupancy.to_json(orient='records'))

@app.route("/one_occupancy/api/one_training/occupancy", methods=['GET'])
def api_one_occupancy():
        '''Returns the history of the occupancy and max occupancy for the requested center_id in a json format.
        The centre_id is passt via get request argument.
        '''
        
       
        request_arguments = {}
        # Read the get argument
        if (request.args.get('centre_id')):
            request_arguments['centre_id'] = request.args.get('centre_id')
        else:
            request_arguments['centre_id'] = 117
        if request.args.get('weekday'):
            request_arguments['weekday'] = int(request.args.get('weekday'))
        else:
            request_arguments['weekday'] = 0
            
        print(request_arguments)
        print(datetime.datetime.today().weekday())
        
        # Query the centre name for the specific centre id 
        cnxn = SQLiteConnector(path_to_database)
        centre_prop = cnxn.query_data("SELECT * FROM centres WHERE centre_id = " + str(request_arguments['centre_id']) ) #Returns (centre_id, centre_name)
        centre_name = centre_prop[0][1]
        cnxn.close_connection()
        

        # Query the history of the occupancy for the specific centre
        # Request only the last day  %H:%M:%S
        ts = datetime.date.today() - datetime.timedelta(days=360)
        start_time = ts.strftime("%Y-%m-%d")
        
        query = """SELECT * FROM occupancy WHERE centre_id = """ + str(request_arguments['centre_id']) + """ 
                                            AND timestamp >= '""" + start_time + """'
                                            ORDER BY id"""
        cnxn = SQLiteConnector(path_to_database)
        
        # Create pandas dataframe
        occupancy_df = pd.read_sql_query(query, cnxn.connection)
        cnxn.close_connection()
        
        #Convert to pd datetime
        occupancy_df['timestamp'] = pd.to_datetime(occupancy_df['timestamp'])
        # Convert uct to local time
        occupancy_df['timestamp'] = occupancy_df['timestamp'].dt.tz_localize('utc', ambiguous='infer').dt.tz_convert('Europe/Vienna')
        # Round time to 15 min so that it can be averaged over time
        occupancy_df['timestamp_round_time'] = pd.to_datetime(occupancy_df['timestamp'], format='%H:%M').dt.round('15min', ambiguous='infer', nonexistent="NaT").dt.time
        # Add Weekday column
        occupancy_df['weekday'] = [ts.weekday() for ind, ts in enumerate(occupancy_df['timestamp'])]
        
        weekday_today = datetime.datetime.today().weekday()
        weekday_difference = weekday_today - request_arguments['weekday'] 
        
        # # Debugging:
        weekday = (datetime.datetime.today() - datetime.timedelta(days=weekday_difference)).weekday()
        #weekday = datetime.datetime.today().weekday()
        
        # Group by weekday
        occupancy_df_weekday = occupancy_df[occupancy_df['weekday'] == weekday]
        
        occupancy_df_grouped_by_time = occupancy_df_weekday.groupby(['timestamp_round_time'])#['currentVisitors'].describe()
        occupancy_df_grouped_by_time_statistic = occupancy_df_grouped_by_time['currentVisitors'].describe()
        occupancy_df_grouped_by_time_statistic['std'] = occupancy_df_grouped_by_time_statistic['std'].fillna(0)
        
        
        
        occupancy_mean = occupancy_df_grouped_by_time_statistic['mean'].to_numpy()
        occupancy_std  = occupancy_df_grouped_by_time_statistic['std'].to_numpy()
        
        # Extract the history of the maximum occupancy
        max_occupancy = occupancy_df_weekday.maxVisitors.to_numpy()
        
        
        # Generate labels
        # For each entry, the label looks as 07:15;Samstag.        
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        round_times_list = [key.strftime("%H:%M") for key, _ in occupancy_df_grouped_by_time]
        weekdays_list = occupancy_df_weekday['weekday'].tolist()
        labels = [round_times_list[i] + ";" + weekdays[weekdays_list[i]] for i in range(len(round_times_list))]
        
        
        
        # Todays occupancy
        #today_date = datetime.datetime.today().date()  # Debugging: - datetime.timedelta(days=0)
        today_date = datetime.datetime.today().date() - datetime.timedelta(days=weekday_difference)
        occupancy_df_today  = occupancy_df[pd.to_datetime(occupancy_df['timestamp']).dt.date == today_date]['currentVisitors'].to_numpy()
        
        occupancy_today = [0]
        
        for i in range(len(occupancy_mean)):
            if i < len(occupancy_df_today):
                occupancy_today.append(int(occupancy_df_today[i]))
            else:
                occupancy_today.append('NaN')
        
        pd.set_option('display.max_rows', None)
        
        # Generate response json structure
        occupancy_history = {labels[i]: {'occupancy': occupancy_mean[i], 'occupancy_std': occupancy_std[i], 'max_occupancy': int(max_occupancy[i]), 'occupancy_today': occupancy_today[i]} for i in range(len(occupancy_mean))}
        centre_properties  = {'centre_properties': {'centre_id': request_arguments['centre_id'], 'name': centre_name}, 'occupancy_history': occupancy_history}
        response = jsonify(centre_properties)
        
        # Add header to the response to allow cross origin requests
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


@app.route("/one_occupancy")
def one_occupancy():
        '''
        Renders the one_occupancy.html template. The most current occupancy is requested and past to the template where
        it is visualized via doughnut charts for each centre. 
        ''' 
        
        # Request all the center names
        cnxn = SQLiteConnector(path_to_database)
        centres = cnxn.query_data("SELECT * FROM centres") # Returns (centre_id, centre_name)
        cnxn.close_connection()
        centre_ids = [centre[0] for centre in centres]
        centre_names = [centre[1] for centre in centres]
        
        
        # Request the most current centre occupancy for each centre
        current_occupancy = []
        current_max_occupancy = []
        centre_last_update = []
        for i, centre_id in enumerate(centre_ids):
                cnxn = SQLiteConnector(path_to_database)
                centre_occupancy = cnxn.query_data("""SELECT * FROM occupancy WHERE 
                                                        centre_id = """ + str(centre_id) + """
                                                        AND timestamp >=  '2020-10-31' 
                                                        AND timestamp IN (SELECT max(timestamp) FROM occupancy)"""
                                                  )
                cnxn.close_connection()
                if not centre_occupancy:
                    print(str(centre_id) + ": Data not available ")
                    current_occupancy.append(0)
                    current_max_occupancy.append(0)
                    centre_last_update.append(0)
                    
                else:
                    current_occupancy.append(centre_occupancy[0][2])
                    current_max_occupancy.append(centre_occupancy[0][3])
                    centre_last_update.append(centre_occupancy[0][4])
                    
        # Create the labels for the doughnut charts (e.g. 10%) 
        # If current_max_occupancy is 0, this means that the centre is closed.
        current_occupancy_percent = []
        for i in range(len(current_max_occupancy)):     
            if current_max_occupancy[i] == 0:
                current_occupancy_percent.append(current_occupancy[i])
            else:
                current_occupancy_percent.append(str(int(np.round(current_occupancy[i]/current_max_occupancy[i]*100))) + '%')
                
        # Define the color for the doughnut plot 
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
                current_color.append(color_green)

        
        # Reshape the update time 
        dtd = datetime.datetime.strptime(centre_last_update[0], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=2)
        last_update = dtd.strftime("%d.%m.%Y, %H:%M")
        
        
        # Render the html template
        return render_template("one_occupancy.html", len = len(centre_names), centre_ids = centre_ids, centres = centre_names, current_occupancy_percent = current_occupancy_percent, current_occupancy = current_occupancy, current_max_occupancy = current_max_occupancy, current_color=current_color, last_update = last_update)


@app.route("/one_occupancy/analysis")
def one_occupancy_analysis():
    return render_template("one_occupancy_analysis.html")


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0')
        

