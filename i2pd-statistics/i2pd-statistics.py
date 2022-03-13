#!/usr/bin/env python3
#
#

import os
import re
import requests
import sys

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
    
def process_netstatus(inp):
    ''' Extract the reported network status
    
    Valid values are defined here https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L223
    '''
    return inp.split("</b>")[1].lstrip()
    
def process_percentage(inp):
    ''' Extract a percentage value
    '''
    
    perc = getMatches(inp, "([0-9,\.]+)%")
    if len(perc) == 0:
        return 0
    else:
        return perc[0]


def extract_number(inp):
    ''' Extract an integer
    '''
    i = getMatches(inp, "([0-9]+)")    
    if len(i) == 0:
        i = ["0"]
        
    return int(i[0])


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
    
    # We _should_ now have a volume - it needs converting to bytes
    if unit == "KiB":
        vol = float(volume[0]) * 1024
    elif unit == "MiB":
        vol = (float(volume[0]) * 1024) * 1024
    elif unit == "GiB":
        vol = ((float(volume[0]) * 1024) * 1024) * 1024
    
    # Now we need to do the same to extract calculated throughput
    # that's always kibibits (https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L289)
    throughp = getMatches(inp, "([0-9,\.]+) KiB/s")
    if len(throughp) == 0:
        throughp = ['0']
    
    # Convert to bit/s
    through = (float(throughp[0]) * 1024) * 8
    
    # There's some float maths nastiness in I2PD - it claims to have sent fractions of bytes
    # (and for that matter, bits). Round the value as a "good enough" indicator
    return round(vol), through
    

def extract_version(inp):
    ''' Extract the version string
    '''
    ver = getMatches(inp, "([0-9,\.]+)")
    if len(ver) == 0:
        ver = ['unknown']
        
    return ver[0]
    
def split_counter_row(inp):
    ''' The counter row is a single line with multiple counters on it
    '''
    
    routers = 0
    floodfills = 0
    leasesets = 0
    clienttunnels = 0
    transittunnels = 0
    
    lines = inp.split('<b>')
    for line in lines:    
        if line.startswith("Routers:"):
            routers = extract_number(line)
        elif line.startswith("Floodfills:"):
            floodfills = extract_number(line)
        elif line.startswith("LeaseSets:"):
            leasesets = extract_number(line)
        elif line.startswith("Client Tunnels:"):
            clienttunnels = extract_number(line)       
        elif line.startswith("Transit Tunnels:"):
            transittunnels = extract_number(line)
        
    return routers, floodfills, leasesets, clienttunnels, transittunnels




stats_status = "available"

# We grab pages to begin with - we don't want too much delay between page reads
# otherwise stats might diverge
try:
    homepage = getPage("/", HOST)
    tunnels_page = getPage("/?page=tunnels", HOST)
except:
    stats_status = "unavailable"
    
    tags = "url={url},statspage_status={stats_status}".format(
                            url = HOST,    
                            stats_status = stats_status
                            )    
    
    lp = "{measurement},{tags} failed=1".format(
                            measurement = MEASUREMENT,
                            tags = tags
                            )
    print(lp)    
    sys.exit()


bold_fields = getMatches(homepage, "<b>(.+)<br>")
#print(bold_fields)

network_status_v6 = "disabled"

for line in bold_fields:
    if line.startswith("Uptime:"):
        uptime = process_uptime(line)
    if line.startswith("Network status:"):
        network_status = process_netstatus(line)
    if line.startswith("Network status v6:"):
        network_status_v6 = process_netstatus(line)
    elif line.startswith("Tunnel creation success rate:"):
        creation_success = process_percentage(line)
    elif line.startswith("Received:"):
        in_vol, in_through = extract_throughput(line)
    elif line.startswith("Sent:"):
        out_vol, out_through = extract_throughput(line)
    elif line.startswith("Transit:"):
        transit_vol, transit_through = extract_throughput(line)
    elif line.startswith("Version:"):
        version = extract_version(line)
    elif line.startswith("Routers:"):
        routers, floodfills, leasesets, x, y = split_counter_row(line)
    elif line.startswith("Client Tunnels:"):
        x, y, z, clienttunnels, transittunnels = split_counter_row(line)
        

# This is narsty.... 
page_split = tunnels_page.split("<b>Outbound tunnels:</b>")

inbound = {
    "tunnels" : 0,
    "expiring" : 0,
    "established" : 0,
    "exploring" : 0
    }

outbound = {
    "tunnels" : 0,
    "expiring" : 0,
    "established" : 0,
    "exploring" : 0
    }



for line in page_split[0].split("\n"):
    if line.startswith('<div class="listitem">'):
        inbound['tunnels'] += 1            
        if "tunnel expiring" in line:
            inbound['expiring'] += 1
        elif "tunnel established" in line:
            inbound['established'] += 1
            if "(exploratory)" in line:
                inbound['established'] += 1


for line in page_split[1].split("\n"):
    if line.startswith('<div class="listitem">'):
        outbound['tunnels'] += 1
        if "tunnel expiring" in line:
            outbound['expiring'] += 1
        elif "tunnel established" in line:
            outbound['established'] += 1
            if "(exploratory)" in line:
                outbound['established'] += 1


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

fields = "{fields},routers={routers}i,floodfills={floodfills}i,leasesets={leasesets}i,clienttunnels={clienttunnels}i,transittunnels={transittunnels}i".format(
                        fields = fields,
                        routers = routers,
                        floodfills = floodfills,
                        leasesets = leasesets,
                        clienttunnels = clienttunnels,
                        transittunnels = transittunnels
                        )


fields = "{fields},inbound_tunnel_count={inbound_tunnels}i,inbound_tunnels_expiring={inbound_tunnels_expiring}i,inbound_tunnels_established={inbound_tunnels_established}i,inbound_tunnels_exploratory={inbound_tunnels_exploratory}i".format(
                        fields = fields,
                        inbound_tunnels = inbound['tunnels'],
                        inbound_tunnels_expiring = inbound['expiring'],
                        inbound_tunnels_established = inbound['established'],
                        inbound_tunnels_exploratory = inbound['exploring']
                        )


fields = "{fields},outbound_tunnel_count={outbound_tunnels}i,outbound_tunnels_expiring={outbound_tunnels_expiring}i,outbound_tunnels_established={outbound_tunnels_established}i,outbound_tunnels_exploratory={outbound_tunnels_exploratory}i".format(
                        fields = fields,
                        outbound_tunnels = outbound['tunnels'],
                        outbound_tunnels_expiring = outbound['expiring'],
                        outbound_tunnels_established = outbound['established'],
                        outbound_tunnels_exploratory = outbound['exploring']
                        )

tags = "url={url},version={version},network_status={network_status},network_status_v6={network_status_v6}".format(
                        url = HOST,    
                        version = version,
                        network_status = network_status,
                        network_status_v6 = network_status_v6
                        )

lp = "{measurement},{tags} {fields}".format(
                        measurement = MEASUREMENT,
                        tags = tags,
                        fields = fields
                        )

print(lp)
