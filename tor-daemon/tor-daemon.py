#!/usr/bin/env python3
#
# Telegraf Exec plugin to monitor the tor daemon
#
# Copyright (c) 2022 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#
#

import datetime
import os
import socket
import sys
import time

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
    read_attempts = 0
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            l = data.decode()
            res.append(l)
            
            if l.startswith("250 OK\r\n") or l.endswith("250 OK\r\n"):
                # We've reached the end of the message
                break
            
        except socket.timeout as e:
            if e.args[0] == "timed out":
                if len(res) == 0 and read_attempts < 2 and len(res) == 0:
                    # Wait a little longer
                    time.sleep(0.5)
                    read_attempts += 1
                    continue
                else:
                    # Looks like we got our read
                    break
            else:
                # Unhandled error
                print(e)
                sys.exit(1)
        except socket.error as e:
            print(e)
            sys.exit(1)
            
    return ''.join(res).split('\r\n')


def get_guard_counts(s):
    ''' Get guard info and build a set of counters
    
    '''
    res = send_and_respond(s, "GETINFO entry-guards")
    
    if len(res) < 1 or not res[0].startswith("250+"):
        print("failed to get guard info")
        return {}
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


def get_exit_policy_stats(s):
    ''' Get exit policies (if set) and generate stats based on them
    
    Returns a list of statistics
    
    utilities/telegraf-plugins#4
    '''
    
    stats = []
    is_relay = {
        "name" : "server_mode_enabled",
        "type" : "string",
        "value" : "1",
        "fieldtype" : "tag"
        }
    
    # Fetch the ipv4 policy
    res = send_and_respond(s, "GETINFO exit-policy/ipv4")
    if len(res) < 1 or not res[0].startswith("250"):
        # We're not a relay
        is_relay["value"] = "0"
        stats.append(is_relay)
        return stats
    
    
    # We have exit policies of some form
    stats.append(is_relay)
    
    ipv4_stats = process_exit_policy(res)
    
    for stat in ipv4_stats:
        p = {
            "name" : "ipv4_exit_policy_num_" + stat,
            "type" : "int",
            "value" : ipv4_stats[stat],
            "fieldtype" : "field"
            }
        stats.append(p)
        
    # Now do the same for ipv6 policies
    res = send_and_respond(s, "GETINFO exit-policy/ipv6")
    if len(res) < 1 or not res[0].startswith("250"):
        # can't proceed, so return what we've got
        return stats
    
    
    ipv6_stats = process_exit_policy(res)
    for stat in ipv6_stats:
        p = {
            "name" : "ipv6_exit_policy_num_" + stat,
            "type" : "int",
            "value" : ipv6_stats[stat],
            "fieldtype" : "field"
            }
        stats.append(p)
    
    return stats
    
    
def process_exit_policy(policy_lines):
    ''' Take a policy response line and derive stats from it
    
    Returns a counters dict
    
    utilities/telegraf-plugins#4
    '''
    
    
    # The result that comes back will vary, sometimes it's single-line
    # sometimes it's multiline
    lines = []
    if policy_lines[0].startswith("250+"):
        # multi-line
        for line in policy_lines:
            if line in [".", "250 OK"]:
                break
            if "=" in line:
                # First line
                lines.append(line.split("=")[1])
            else:
                # subsequent lines
                lines.append(line)
    else:
        # single line
        lines.append(policy_lines[0].split("=")[1])
    
    
    # Set up the counters
    counters = {
        "total" : 0,
        "accept" : 0,
        "reject" : 0,
        "wildcard" : 0,
        "specific" : 0,
        "unique_hosts" : 0,
        "unique_ports" : 0,
        "wildcard_port" : 0,
        "specific_port" : 0,
        "port_range": 0,
        
 
        # Policy specific counters
        "wildcard_accept" : 0,
        "specific_accept" : 0,
        "wildcard_port_accept" : 0,
        "specific_port_accept" : 0,
        
        
        "wildcard_reject" : 0,
        "specific_reject" : 0,
        "wildcard_port_reject" : 0,
        "specific_port_reject" : 0,
        
        }
    
    hosts = []
    ports = []
    
    counts = {
        "accept" : {"hosts" : [], "ports" : []},
        "reject" : {"hosts" : [], "ports" : []}
        }
    
    for policy_line in lines:
        if len(policy_line) == 0:
            continue
        # The policies are comma delimited for single line entries
        policies = policy_line.split(",")
        counters["total"] += len(policies)
        
        # iterate over the policies and update counters
        for policy in policies:
            parts = policy.split(" ")
            if parts[0].startswith("accept"):
                counters["accept"] += 1
                mode = "accept"
            else:
                counters["reject"] += 1
                mode = "reject"
                
            if parts[1].startswith("*"):
                counters["wildcard"] += 1
                counters["wildcard_" + mode] += 1
            elif parts[1].startswith("1") or parts[1].startswith("2"):
                counters["specific"] += 1
                counters["specific_" + mode] += 1
                
                # ipv6 complicates this a touch
                ip = ":".join(parts[1].split(":")[0:-1])
                hosts.append(ip)
                counts[mode]["hosts"].append(ip)

            port = parts[1].split(":")[-1]
            
            if "-" in port:
                # It's a range, iterate over it
                counters["port_range"] += 1
                port_parts = [ int(x) for x in port.split("-") ]
                while port_parts[0] <= port_parts[1]:
                    ports.append(port_parts[0])
                    counts[mode]["ports"].append(port_parts[0])
                    counters['specific_port'] += 1
                    counters["specific_port_" + mode] += 1
                    port_parts[0] += 1
                    
            else:
                # Singluar port (or wildcard)
                ports.append(port)
                counts[mode]["ports"].append(port)
                if port == "*":
                    counters['wildcard_port'] += 1
                    counters["wildcard_port_" + mode] += 1
                else:
                    counters['specific_port'] += 1
                    counters["specific_port_" + mode] += 1
        
    # Calculate the unique counts
    counters["unique_hosts"] = len(set(hosts))
    counters["unique_ports"] = len(set(ports))

    counters["unique_hosts_accept"] = len(set(counts["accept"]["hosts"]))
    counters["unique_ports_accept"] = len(set(counts["accept"]["ports"]))
    counters["unique_hosts_reject"] = len(set(counts["accept"]["hosts"]))
    counters["unique_ports_reject"] = len(set(counts["accept"]["ports"]))


    
    return counters
    

def get_accounting_info(s):
    
    byte_fields = [
        ["accounting/bytes", "accounting_bytes", "int", "field"],
        ["accounting/bytes-left", "accounting_bytes_remaining", "int", "field"],
    ]
    
    vals = []    
    
    accounting = { 
        "name" : "accounting_enabled",
        "type" : "string",
        "value" : "0",
        "fieldtype" : "tag"
        }
    
    res = send_and_respond(s, "GETINFO accounting/enabled")
    if len(res) < 1 or not res[0].startswith("250-"):
        return vals
    
    v = int(res[0].split("=")[1])
    if v == 0:
        vals.append(accounting)
        return vals
    
    
    # Accounting is active
    accounting['value'] = "1"
    vals.append(accounting)
    
    # Current relay state
    res = send_and_respond(s, "GETINFO accounting/hibernating")
    if len(res) > 1 and res[0].startswith("250-"):
            val = res[0].split("=")[1]
            vals.append({
                    "name" : "accounting_hibernating_state",
                    "type" : "string",
                    "value" : val,
                    "fieldtype" : "tag"
                })
    
    # bytes
    for f in byte_fields:
        res = send_and_respond(s, "GETINFO " + f[0])
        if len(res) > 1 and res[0].startswith("250-"):
            val = res[0].split("=")[1]
            # There's a read and a write value
            cols = val.split(" ")
            
            vals.append({
                    "name" : f[1] + "_read",
                    "type" : f[2],
                    "value" : int(cols[0]),
                    "fieldtype" : f[3]
                })
            
            vals.append({
                    "name" : f[1] + "_write",
                    "type" : f[2],
                    "value" : int(cols[1]),
                    "fieldtype" : f[3]
                })
            

    # Calculate durations
    #
    # We get values like 
    #
    # 2022-05-04 12:31:00
    #
    # We want to convert these into durations
    #
    # How much of the accounting interval is left? how much has elapsed etc

    # strptime pattern to use when parsing tor's date responses
    timepattern = "%Y-%m-%d %H:%M:%S"
    
    # For some reason, tor uses rfc3339 for the current time, but not for
    # accounting times.
    nowtimepattern = "%Y-%m-%dT%H:%M:%S"

    # Ask Tor what time it thinks it currently is
    res = send_and_respond(s, "GETINFO current-time/utc")
    if len(res) > 1 and res[0].startswith("250-"):
        val = res[0].split("=")[1]
        now = datetime.datetime.strptime(val, nowtimepattern)
    
    # Now ask when the accounting period started
    res = send_and_respond(s, "GETINFO accounting/interval-start")
    if len(res) > 1 and res[0].startswith("250-"):
        val = res[0].split("=")[1]
        acc_start = datetime.datetime.strptime(val, timepattern)
        
        # subtract from now
        delta = now - acc_start
        vals.append({
            "name" : "accounting_period_seconds_elapsed",
            "type" : "int",
            "value" : int(delta.total_seconds()),
            "fieldtype" : "field"            
            })
        
    # When does the accounting period end?
    res = send_and_respond(s, "GETINFO accounting/interval-end")
    if len(res) > 1 and res[0].startswith("250-"):
        val = res[0].split("=")[1]
        acc_stop = datetime.datetime.strptime(val, timepattern)
        
        # subtract now
        delta = acc_stop - now
        vals.append({
            "name" : "accounting_period_seconds_remaining",
            "type" : "int",
            "value" : int(delta.total_seconds()),
            "fieldtype" : "field"            
            })
            
            
    # Calculate length of the accounting period
    delta = acc_stop - acc_start
    vals.append({
        "name" : "accounting_period_length",
        "type" : "int",
        "value" : int(delta.total_seconds()),
        "fieldtype" : "field"            
        })    
    return vals

    
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
                v = entry['name'] + "=" + str(entry["value"]) + "i"
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
    # set a read timeout of 0.2s
    s.settimeout(0.2) 
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

# Get accounting info
for v in get_accounting_info(s):
    state["stats"].append(v)


# Get exit policy info
for v in get_exit_policy_stats(s):
    state["stats"].append(v)

#print(state)
print(build_lp(MEASUREMENT, state))
