#!/usr/bin/env python3
#
# Telegraf plugin to collect logs from
# pihole and generate per-client stats 
#
# Copyright (c) 2023 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#

import requests
import sys
from datetime import datetime, timedelta

# Pihole connection info
PIHOLE_ADDRESS="http://127.0.0.1:8080"

# Auth token - get this from settings
PIHOLE_TOKEN=""

# How many minutes of logs to query on each
# iteration
QUERY_TIME_RANGE=15

# The measurement name to use
MEASUREMENT="pihole_clients"



def getQueryLogs(pihole_addr, token, time_range):
    ''' Build a request to the Pihole API to get query logs for the 
    specified time range
    '''
    # Calculate the time bounds
    now = datetime.now()
    end_s = now.strftime('%s')
    
    # Calculate the startt time and round it to the 
    # nearest full minute
    start = now - timedelta(minutes = time_range)
    start_str = start.strftime('%s')
    start_s = int(int(start_str)//60 * 60)

    # Build the request
    args = {
        "from" : start_s,
        "until" : end_s,
        "auth" : token
        }
    url = f"{pihole_addr}/admin/api.php?getAllQueries"
    
    # Place and return
    r = requests.get(url=url, params=args)
    return r.json()


def queryLogToStats(queries):
    ''' Iterate over the query log results and build a stats object
    
    '''
    # Define the structures that we'll collect stats into
    answer_types = {
                "blocklisted" : 0,
                "forwarded" : 0,
                "cachedresponse" : 0,
                "wildcardblock" : 0,
                "total" : 0
                }

    counters = {
            "clients" : {}
        }

    results = {}

    # Iterate over the result  set
    for row in queries['data']:
        # Round the timestamp to the nearest minute 
        ts = int(int(row[0])//60 * 60)
        
        # Client etc
        client = row[3]
        resp_type = int(row[4])
        
        # Translate the response type into a string
        if resp_type == 1:
            answer_type = "blocklisted"
        elif resp_type == 2:
            answer_type = "forwarded"    
        elif resp_type == 3:
            answer_type = "cachedresponse"    
        elif resp_type == 4:
            answer_type = "wildcardblock"    
            
        # Populate the stats objects if not already there
        ts_key = ts
        if ts_key not in results:
            results[ts_key] = counters.copy()
            
        if client not in results[ts_key]["clients"]:
            results[ts_key]["clients"][client] = answer_types.copy()

        # Increment the relevant counters
        results[ts_key]["clients"][client][answer_type] += 1
        results[ts_key]["clients"][client]["total"] += 1

    return results


def statsBlockToLP(measurement, block, client, timestamp):
    ''' Convert an "answer_types" stats block to line protocol
    '''
    lps = [
        measurement,
        f"client={client}"
        ]
    
    lp1 = ','.join(lps)
    
    fields = []
    
    for answer_type in block:
        fields.append(f"{answer_type}={block[answer_type]}i")

    lp2 = ','.join(fields)
    lp = " ".join([lp1, lp2, str(timestamp * 1000000000)])
    return lp
    

def statsToLP(measurement, stats):
    ''' Iterate over the stats object creating line protocol for
    each client and timestamp pair
    '''
    lines = []
    # Iterate over each timestamp grouping
    for timestamp in stats:       
        # Iterate over the clients
        for client in stats[timestamp]["clients"]:
            lp = statsBlockToLP(measurement, stats[timestamp]["clients"][client], client, timestamp)
            lines.append(lp)            
        
    return lines
    

if __name__ == "__main__":
    # Get a list of queries
    queries = getQueryLogs(PIHOLE_ADDRESS, PIHOLE_TOKEN, QUERY_TIME_RANGE)

    if "data" not in queries:
        # Request failed
        sys.exit(1)
        

    stats = queryLogToStats(queries)

    lp_lines = statsToLP(MEASUREMENT, stats)
    print('\n'.join(lp_lines))
