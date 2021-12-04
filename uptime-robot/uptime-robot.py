#!/usr/bin/env python3
#
#
# Hit the Uptime Robot API to fetch response times and status
#
# Copyright (c) 2021 B Tasker
#
import requests

BASE_URL="https://api.uptimerobot.com/v2"
API_KEY="" # Get this from "my_settings" in the uptime robot dashboard
MEASUREMENT_NAME="website_response_times" # Measurement name in Influxdb
db_name="websites" # I use this for output routing in Telegraf's config, you can leave it blank

def placeRequest(path, data):
    ''' Place a request against the UptimeRobot API and return a dict
    '''
    headers = {
    'content-type': "application/x-www-form-urlencoded",
    'cache-control': "no-cache"
    }
    
    data['api_key'] = API_KEY
    data['format'] = "json"

    r = requests.post(f"{BASE_URL}{path}", headers=headers, data=data)
    #print(r.text)
    return r.json()


def writeLP(m):
    ''' Convert a monitor object to line protocol and print it
    '''
    tagset=f"url={m['url']},id={m['id']},influxdb_database={db_name}"
    print(f"{MEASUREMENT_NAME},{tagset} status={m['status']},avg_response={m['average_response_time']}")
    
    # Iterate over the response time logs
    for responsetime in m['responsetimes']:
        print(f"{MEASUREMENT_NAME},{tagset} response_time={responsetime['value']}i {int(responsetime['datetime']) * 1000000000}")


    
    
x = {
    "response_times" : 1, # Include response times
    "response_times_average" : 15, # 15 min intervals
    "response_times_limit" : 16, # return the last 4 hours - 4*4
    }
logs = placeRequest("/getMonitors", x)

for monitor in logs['monitors']:
    writeLP(monitor)



