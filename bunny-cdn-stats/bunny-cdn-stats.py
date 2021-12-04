#!/usr/bin/env python3
#
# Telegraf Exec plugin to poll BunnyCDN's API and retrieve stats
#
# Copyright (c) 2021 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#
#
import requests
import sys
import time

from datetime import datetime

token = sys.argv[1]
url = "https://api.bunny.net"
measurement = "bunnycdn"


def getStats(start, pullzone, token):
    params = {
        'dateFrom' : start,
        'pullZone' : pullzone,
        'loadErrors' : True,
        'hourly' : True
    }
    headers = {"Accept": "application/json",
               "AccessKey" : token
               }
    r = requests.request("GET", f"{url}/statistics", headers=headers, params=params)
    return r.json()
    
    
def getPullZones(token):
    
    headers = {"Accept": "application/json",
               "AccessKey" : token
               }
    r = requests.request("GET", f"{url}/pullzone", headers=headers)
    return r.json()    


def process_stats_block(stats_block, measurement, tagset, field_name):
    '''
    
    '''
    lines = []
    for key in stats_block:
        # Key is the time, turn it into a timestamp
        ts = datetime.strptime(key, '%Y-%m-%dT%H:%M:%SZ').strftime('%s')
        value = stats_block[key]
        lines.append([
            f"{measurement},{tagset} {field_name}={value} {ts}"
            ])
        
    return lines

    
    
def process_stats_blocks(stats, measurement, tagset):
    '''
    
    '''
    lines = []
    for key in stats['OriginTrafficChart']:
        # Key is the time, turn it into a timestamp
        ts = datetime.strptime(key, '%Y-%m-%dT%H:%M:%SZ').strftime('%s')
        
        fields = [
            f"origin_bytes={int(stats['OriginTrafficChart'][key])}i",
            f'status_3xx={int(stats["Error3xxChart"][key])}i',
            f'status_4xx={int(stats["Error4xxChart"][key])}i',
            f'status_5xx={int(stats["Error5xxChart"][key])}i',
            
            f'origin_response_time={stats["OriginResponseTimeChart"][key]}',
            f'shield_bytes={int(stats["OriginShieldInternalBandwidthUsedChart"][key])}i',
            f'edge_bytes={int(stats["BandwidthUsedChart"][key])}i',
            
            f'requests_served={int(stats["RequestsServedChart"][key])}i',
            f'RHR={stats["CacheHitRateChart"][key]}'            
            ]
        
        lines.append(
            f"{measurement},{tagset} {','.join(fields)} {ts}"
            )
        
    return lines    
    
    
    
dt = datetime.today()
midnight = datetime.combine(dt, datetime.min.time()).strftime('%Y-%m-%dT%H:%M:%SZ')

ts = int(time.time())
lines = []
pullzones = getPullZones(token)
for zone in pullzones:
    stats = getStats(midnight,zone['Id'], token)
    #print(stats)
    num_rules = len(zone['EdgeRules'])
    zone_name = zone['Name']
    
    tagset = f'edge_zone={zone_name}'
    
    lines.append(
        f'{measurement},{tagset} total_bandwidth_used={stats["TotalBandwidthUsed"]},total_origin_traffic={stats["TotalOriginTraffic"]},mean_origin_response_time={stats["AverageOriginResponseTime"]},total_requests_served={stats["TotalRequestsServed"]},mean_rhr={stats["CacheHitRate"]} {ts}'
        )
    '''
    r30xs = process_stats_block(stats["Error3xxChart"], measurement, tagset, "status_3xx")
    r40xs = process_stats_block(stats["Error4xxChart"], measurement, tagset, "status_4xx")
    r50xs = process_stats_block(stats["Error5xxChart"], measurement, tagset, "status_5xx")
    origin_response_times = process_stats_block(stats["OriginResponseTimeChart"], measurement, tagset, "origin_response_time")       
    
    origin_bytes = process_stats_block(stats["OriginTrafficChart"], measurement, tagset, "origin_bytes")
    shield_bytes = process_stats_block(stats["OriginShieldInternalBandwidthUsedChart"], measurement, tagset, "shield_cache_bytes")
    edge_bytes = process_stats_block(stats["BandwidthUsedChart"], measurement, tagset, "edge_bytes")
    
    
    requests_served = process_stats_block(stats["RequestsServedChart"], measurement, tagset, "RequestsServedChart")
    rhr = requests_served = process_stats_block(stats["CacheHitRateChart"], measurement, tagset, "RHR")
    
    
    
    # Merge the lists
    lines = lines + r30xs + r40xs + r50xs
    '''
    
    lines = lines + process_stats_blocks(stats, measurement, tagset)
    
    
print('\n'.join(lines))
