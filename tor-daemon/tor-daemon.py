#!/usr/bin/env python3
import os
import socket
import sys

CONTROL_H = os.getenv("CONTROL_HOST", "127.0.0.1")
CONTROL_P = int(os.getenv("CONTROL_PORT", 9051))
AUTH = os.getenv("CONTROL_AUTH", "MySecretPass")
MEASUREMENT = os.getenv("MEASUREMENT", "tor")

# stats to collect
stats = [
    #cmd, output_name, type, tag/field
    ["traffic/read", "bytes_rx", "int", "field"],
    ["traffic/written", "bytes_tx", "int", "field"],
    ["uptime", "uptime", "int", "field"],
    ["version", "tor_version", "string", "field"],
    ["dormant", "dormant", "int", "field"],
    ["status/reachability-succeeded/or", "orport_reachability", "int", "field"],
    ["status/reachability-succeeded/dir", "dirport_reachability", "int", "field"],
    
    ["status/version/current", "version_status", "string", "tag"],
    ["network-liveness", "network_liveness", "string", "tag"]
]


def send_and_respond(sock, command):
    ''' Send a command and return a list of response lines
    '''
    
    if not command.endswith('\n'):
        command += "\n"

    a = sock.sendall(command.encode())

    # Read the response
    res = []
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            res.append(data.decode())
        except BlockingIOError:
            break
            
    return ''.join(res).split('\r\n')


def get_guard_counts(s):
    ''' Get guard info and build a set of counters
    
    '''
    res = send_and_respond(s, "GETINFO entry-guards")
    
    if len(res) < 1 or not res[0].startswith("250+"):
        print("failed to get guard info")
    else:
        # Strip the response code and trailers
        counters = {
            "never-connected" : 0,
            "down" : 0,
            "up" : 0,
            "unusable" : 0,
            "unlisted" : 0,
            "total" : 0
            }
        
        for line in res[0:-2]:
            s = line.split(" ")
            if len(s) < 2:
                continue
            
            counters[s[1]] += 1
            counters["total"] += 1
    
    return counters
    
    
def build_lp(measurement_name, state):
    ''' Build a Line Protocol response
    '''
    
    lead = [ measurement_name ]
    fields = []
    
    lead.append("controlport_connection=" + state['conn_status'])
    fields.append("stats_fetch_failures=" + str(state["stats_failures"]) + "i")
    
    for entry in state["stats"]:
        if entry['fieldtype'] == "tag":
            v = entry['name'] + "=" + entry["value"].replace(" ","\ ")
            lead.append(v)
        else:
            # It's a field
            if entry['type'] == "int":
                v = entry['name'] + "=" + entry["value"] + "i"
            elif entry['type'] == "float":
                v = entry['name'] + "=" + entry["value"]
            else:
                v = entry['name'] + '="' + entry["value"] + '"'
            fields.append(v)
            
            
    # Process counters - these are always ints
    for counter in state["counters"]:
        # First list element is a category for the counters
        # e.g. guards
        prefix = counter[0] + "_"
        for nm in counter[1]:
            # Take the name and prepend the prefix, gives us
            # something like
            # guards_down
            fname = prefix + nm.replace("-","_")
            
            # Add the value
            v = fname + "=" + str(counter[1][nm]) + "i"
            fields.append(v)
    
    # Append any tags that have been pushed into the main state object
    for tag in state["tags"]:
        v = tag[0] + "=" + tag[1]
        lead.append(v)
        
    
    l = ",".join(lead)
    f = ",".join(fields)
    return " ".join([l, f])

    
state = {
    "conn_status" : "failed",
    "stats_failures" : 0,
    "stats" : [],
    "counters" : [],
    "tags" : [] # used to track failures etc
}
    
# Initialise a connection
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((CONTROL_H, int(CONTROL_P)))
    s.setblocking(0)
except:
    state["stats_failures"] += 1
    state["tags"].append(["failure_type", "connection"])
    print(build_lp(MEASUREMENT, state))
    sys.exit(1)
   

# Login
cmd = 'AUTHENTICATE "' + AUTH + '"'
res = send_and_respond(s, cmd)       
if len(res) < 1 or res[0] != "250 OK":
    # Login failed
    state["stats_failures"] += 1
    state["tags"].append(["failure_type", "authentication"])
    print(build_lp(MEASUREMENT, state))
    sys.exit(1)


# We manage to login
state["conn_status"] = "success"
    
# Otherwise, start collecting stats
for stat in stats:
    cmd = "GETINFO " + stat[0]
    res = send_and_respond(s, cmd)
    if len(res) < 1 or not res[0].startswith("250-"):
        state["stats_failures"] += 1
        continue
    
    # Otherwise push to the stats list
    val = res[0].split("=")[1]
    
    state["stats"].append({
        "name" : stat[1],
        "type" : stat[2],
        "value" : val,
        "fieldtype" : stat[3]
    })
    

state["counters"].append(["guards", get_guard_counts(s)])

#print(state)
print(build_lp(MEASUREMENT, state))
