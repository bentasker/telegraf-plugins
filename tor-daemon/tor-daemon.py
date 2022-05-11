#!/usr/bin/env python3
import socket
import sys

CONTROL_H = "127.0.0.1"
CONTROL_P = 9051
AUTH = "MySecretPass"
MEASUREMENT="tor"

# stats to collect
stats = [
    #cmd, output_name, type, tag/field
    ["traffic/read", "bytes_rx", "int", "field"],
    ["traffic/written", "bytes_rx", "int", "field"],
    ["uptime", "uptime", "int", "field"],
    ["version", "tor_version", "string", "field"],
    ["dormant", "dormant", "int", "field"],
    ["status/reachability-succeeded/or", "orport_reachability", "int", "field"],
    ["status/reachability-succeeded/dr", "dirport_reachability", "int", "field"],
    
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


def build_lp(measurement_name, state):
    ''' Build a Line Protocol response
    '''
    
    lead = [ measurement_name ]
    fields = []
    
    lead.append("controlport_connection=" + state['conn_status'])
    
    
    for entry in state["stats"]:
        if entry['fieldtype'] == "tag":
            v = entry['name'] + "=" + entry["value"]
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
            
    l = ",".join(lead)
    f = ",".join(fields)
    return " ".join([l, f])

    
state = {
    "conn_status" : "failed",
    "stats" : []
}
    
# Initialise a connection
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((CONTROL_H, int(CONTROL_P)))
s.setblocking(0)


# Login
cmd = 'AUTHENTICATE "' + AUTH + '"'
res = send_and_respond(s, cmd)       
if len(res) < 1 or res[0] != "250 OK":
    # Login failed
    print(state)
    sys.exit(1)


# We manage to login
state["conn_status"] = "success"
    
# Otherwise, start collecting stats
for stat in stats:
    cmd = "GETINFO " + stat[0]
    res = send_and_respond(s, cmd)
    if len(res) < 1 or not res[0].startswith("250-"):
        print("Failed to get stat " + stat[0])
        continue
    
    # Otherwise push to the stats list
    val = res[0].split("=")[1]
    
    state["stats"].append({
        "name" : stat[1],
        "type" : stat[2],
        "value" : val,
        "fieldtype" : stat[3]
    })
    
    
print(state)
print(build_lp(MEASUREMENT, state))
