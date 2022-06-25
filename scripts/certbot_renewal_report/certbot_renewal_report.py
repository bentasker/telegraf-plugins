#!/usr/bin/env python3
#
# Certbot post-deploy hook to report certificate renewals into InfluxDB
# Created in https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/7.html
#
# This script should be put into /etc/letsencrypt/renewal-hooks/deploy
# You can either edit the variables below, or ensure their values are exported into the environment
#
# Copyright (c) 2022 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#

import base64
import os
import requests
import sys
import time

# Config vars - can be manually overriden here or by exporting env vars
measurement = os.getenv("MEASUREMENT", "certbot_renewal")
host = os.getenv("HOSTNAME", os.uname()[1])
influx_url = os.getenv("INFLUXDB_URL", "http://127.0.0.1:8086")
influx_token = os.getenv("INFLUXDB_TOKEN", "")
influx_ver = os.getenv("INFLUXDB_USER", "2") # or 1 for 1.x
influx_bucket = os.getenv("INFLUXDB_BUCKET", "telegraf")


# Don't change this, it's populated by certbot
renewed_domains = os.getenv("RENEWED_DOMAINS", "")

# Get a timestamp
now = time.time_ns()

if len(renewed_domains) < 1:
    # We weren't passed anything
    sys.exit(1)

# split the domains out
domains = renewed_domains.split(" ")

# Get a total count
domain_count = len(domains)

# Create the line protocol prefix that all entries will have
shared_lp = f"{measurement},host={host}"

# Create a list to buffer lines of LP into
lp = [f"{shared_lp},domain=all renewed_count={domain_count} {now}"]

# Iterate over each renewed domain and generate a line of LP
for domain in domains:
    lp.append(f"{shared_lp},domain={domain} renewed_count=1 {now}")
    
# Join our points
lp_str = '\n'.join(lp)

# Now we want to write into InfluxDB
headers = {}
if len(influx_token) > 0:
    # Build an auth header
    if influx_ver == "1":
        # 1.x
        auth_header = f"Basic {base64.b64encode(influx_token.encode())}"
    else:
        auth_header = f"Token {influx_token}"
        
    headers["Authorization"] = auth_header
    
# Build the url
url = f"{influx_url}/api/v2/write?bucket={influx_bucket}"

# Post the data in
r = requests.post(url=url, headers=headers, data=lp_str)

sys.exit(0)
