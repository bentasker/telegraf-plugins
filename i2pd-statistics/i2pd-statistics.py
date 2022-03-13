#!/usr/bin/env python3
#
#

import os
import re
import requests

HOST = os.getenv('I2PD_CONSOLE', 'http://localhost:7070')
MEASUREMENT = os.getenv('MEASUREMENT', 'i2pd')

def getPage(path,host):
    
    r = requests.get(f"{host}{path}")
    return r.text
    

def getMatches(inp, regex):
    return re.findall(regex, inp)
    
def process_uptime(inp):
    ''' Convert x hours, y minutes, z seconds to seconds
    '''
    res = {}
    for unit in ["hours", "minutes", "seconds"]:
        res[unit] = getMatches(inp, "([0-9]+) {}".format(unit))
        if len(res[unit]) == 0:
            res[unit] = ['0']        

    # Convert to seconds
    seconds = (int(res["hours"][0]) * 3600) + (int(res["minutes"][0]) * 60) + int(res["seconds"][0])
    return seconds
    

def process_percentage(inp):
    ''' Extract a percentage value
    '''
    
    perc = getMatches(inp, "([0-9]+)%")
    if len(perc) == 0:
        return 0
    else:
        return perc[0]
    
def extract_throughput(inp):
    ''' The unit changes based on volume, but the minimum unit used is KiB
    
    https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L122
    '''
    
    unit = "KiB"
    volume = getMatches(inp, "([0-9,\.]+) KiB ")
    if len(volume) == 0:
        unit = "MiB"
        volume = getMatches(inp, "([0-9,\.]+) MiB ")
        if len(volume) == 0:
            unit = "MiB"
            volume = getMatches(inp, "([0-9,\.]+) GiB ")
    
    # We _should_ now have a volume - it needs converting to KiB
    if unit == "KiB":
        vol = float(volume[0])
    elif unit == "MiB":
        vol = float(volume[0]) * 1024
    elif unit == "GiB":
        vol = (float(volume[0]) * 1024) * 1024
    
    # Now we need to do the same to extract calculated throughput
    # that's always kibibits (https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L289)
    throughp = getMatches(inp, "([0-9,\.]+) KiB/s")
    if len(throughp) == 0:
        throughp = ['0']
    
    # Convert to bit/s
    through = (float(throughp[0]) * 1024) * 8
    
    return vol, through
    

homepage = getPage("/", HOST)    
#print(homepage)


bold_fields = getMatches(homepage, "<b>(.+)<br>")
#print(bold_fields)

for line in bold_fields:
    if line.startswith("Uptime:"):
        uptime = process_uptime(line)
    elif line.startswith("Tunnel creation success rate:"):
        creation_success = process_percentage(line)
    elif line.startswith("Received:"):
        in_vol, in_through = extract_throughput(line)
    elif line.startswith("Sent:"):
        out_vol, out_through = extract_throughput(line)
    elif line.startswith("Transit:"):
        transit_vol, transit_through = extract_throughput(line)
        


fields = "uptime={uptime}i,tunnel_creation_success_rate={success_rate},in_bytes={in_bytes}i,in_avg_bps={in_bps}".format(
                        uptime = uptime,
                        success_rate = creation_success,
                        in_bytes = in_vol,
                        in_bps = in_through,
                        )


fields = "{fields},out_bytes={out_bytes}i,out_avg_bps={out_bps},transit_bytes={transit_bytes}i,transit_avg_bps={transit_bps}".format(
                        fields = fields,
                        success_rate = creation_success,
                        out_bytes = out_vol,
                        out_bps = out_through,
                        transit_bytes = transit_vol,
                        transit_bps = transit_through
                        )

lp = "{measurement},url={url} {fields}".format(
                        measurement = MEASUREMENT,
                        url = HOST,
                        fields = fields
                        )

print(lp)
