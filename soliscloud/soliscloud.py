#!/usr/bin/env python3
#
# Telegraf exec plugin to poll the Soliscloud API and retrieve
# power measurement data from solar inverters
#
# Note: The soliscloud API is heavily rate limited: 3 requests per 5 seconds
# as a result, this plugin contains some arbitrary sleeps and needs an appropriate
# timeout set in Telegraf's config
#
# Copyright (c) 2023, B Tasker
# Released under BSD 3-Clause License
#

'''
Copyright (c) 2023, B Tasker

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of
conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials
provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used
to endorse or promote products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
import datetime
import base64
import hashlib
import hmac
import json
import os
import requests
import sys
import time


class SolisCloud:

    def __init__(self, config, session=False, debug=False):
        self.config = config
        self.debug = debug
        if session:
            self.session = session
        else:
            self.session = requests.session()

        # Tracking information for rate limit observance
        self.ratelimit = {
            "requests" : 0,
            "lastreset" : time.time()
            }


    def checkRateLimit(self):
        ''' Check how many requests we've made and when
        in order to assess whether we're at risk of hitting
        service rate limits.
        
        The API doc says:
        
            Note: The calling frequency of all interfaces is limited to three times every five seconds for the same IP
        
        It does not clarify whether we'll get a HTTP 429 or some other status
        '''
        
        # What we want to check is
        #
        # Was the last reset more than 5 seconds ago
        # Have there been >= 3 requests?
        #
        now = time.time()
        # When was the last quota reset?
        if (now - self.ratelimit['lastreset']) >= 5:
            self.printDebug(f'RATE_LIMIT_CHECK: Last reset was more than 5 seconds ago')
            # Should be fine, reset the limit
            self.ratelimit['lastreset'] = now
            self.ratelimit['requests'] = 1
            return True
        
        # If we reached this point, we're within the n second boundary
        # check how many requests have been placed
        if (self.ratelimit['requests'] + 1) > self.config['api_rate_limit']:
            self.printDebug(f'RATE_LIMIT_CHECK: Breach - too many requests')
            # We'd be breaching the rate limit
            #
            # We don't increment the counter because we're
            # preventing the request from being sent yet
            return False
        
        # So we're within the time bounds but haven't yet hit the maximum number of
        # requests. Increment the counter and approve the request
        self.printDebug(f'RATE_LIMIT_CHECK: Request approved')
        self.ratelimit['requests'] += 1
        return True


    def createHMAC(self, signstr, secret, algo):
        ''' Create a HMAC of signstr using secret and algo
        
        https://snippets.bentasker.co.uk/page-1910021144-Generate-HMACs-with-different-algorithms-Python3.html
        '''
        hashedver = hmac.new(secret.encode('utf-8'),signstr.encode('utf-8'),algo)
        return hashedver.digest()


    def doAuth(self, key_id, secret, req_path, req_body, method="POST", content_type="application/json", datestring=False):
        ''' Calculate an authorization header value to accompany the request
        
        Solis' API docs describe the method as:
        
            Authorization = "API " + KeyId + ":" + Sign
            Sign = base64(HmacSHA1(KeySecret,
            VERB + "\n"
            + Content-MD5 + "\n"
            + Content-Type + "\n"
            + Date + "\n"
            + CanonicalizedResource))
            
            
        Note: the API wants MD5s and SHA1s to be digests and not hexdigests
        '''
        
        # Calculate an MD5 of the request body
        # if there's no body, the hash should be empty
        if len(req_body) > 0:
            content_md5 = hashlib.md5(req_body.encode()).digest()
            md5_str = base64.b64encode(content_md5).decode()
            self.printDebug(f"Request body: {req_body}")
        else:
            md5_str = ''
            self.printDebug(f"Empty Request body")
        
        # If there's no override, generate the current UTC date
        # in HTTP header format
        if not datestring:
            self.printDebug(f"Calculating date")
            d = datetime.datetime.now(tz=datetime.timezone.utc)
            datestring = d.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Construct the string that we need to sign
        # The entries should be seperated by a newline
        signstr = '\n'.join([method,
                md5_str,
                content_type,
                datestring,
                req_path
                ])
        
        self.printDebug(f"Signstr: {signstr}")
        
        # HMAC and then base64 it
        hmacstr = self.createHMAC(signstr, secret, 'sha1')
        signature = base64.b64encode(hmacstr).decode()
        
        # Take the values and construct the header value
        auth_header = f"API {key_id}:{signature}"
        self.printDebug(f"Calculated Auth header: {auth_header}")
        
        
        # build headers
        headers = {
            "Content-Type" : content_type,
            "Content-MD5" : md5_str,
            "Date" : datestring,
            "Authorization" : auth_header
            }
        
        return headers
    
    
    def fetchInverterDetail(self, inverter_id):
        ''' Fetch detail on a specific inverter
        
        '''
        # Construct the request body
        req_body_d = {
                "id": inverter_id  
            }
               
        req_body = json.dumps(req_body_d)
        req_path = "/v1/api/inverterDetail"
        
        # Construct an auth header
        headers = self.doAuth(self.config['api_id'], self.config['api_secret'], req_path, req_body)
                
        self.printDebug(f'Built request - Headers {headers}, body: {req_body}, path: {req_path}')
                
        # Place the request
        r = self.postRequest(
            f"{self.config['api_url']}{req_path}",
            headers,
            req_body
            )
        
        resp = r.json()
        self.printDebug(f'Fetched inverter {resp}')
        return resp
    
        
    def fetchInverterList(self, station_id=False):
        ''' Fetch the list of inverters.
                
        TODO: may want to implement iterating through pages at some 
            point
        '''
        
        # Construct the request body
        req_body_d = {
                "pageNo": 1,
                "pageSize" : 100        
            }
        
        if station_id:
            req_body_d['stationId'] = station_id
        
        req_body = json.dumps(req_body_d)
        req_path = "/v1/api/inverterList"
        
        # Construct an auth header
        headers = self.doAuth(self.config['api_id'], self.config['api_secret'], req_path, req_body)
        
        self.printDebug(f'Built request - Headers {headers}, body: {req_body}, path: {req_path}')
                
        # Place the request
        r = self.postRequest(
            f"{self.config['api_url']}{req_path}",
            headers,
            req_body
            )
        
        resp = r.json()
        self.printDebug(f'Fetched inverter list: {resp}')
        return resp


    def fetchStationList(self):
        ''' Fetch the list of stations.
        
        In the Solicloud UI these are referred to as plants 
        Basically, the site at which devices are deployed.
        
        So, if you had multiple inverters in one location this
        would return the total values
        
        TODO: may want to implement iterating through pages at some 
            point
        '''
        
        # Construct the request body
        req_body_d = {
                "pageNo": 1,
                "pageSize" : 100        
            }
        req_body = json.dumps(req_body_d)
        req_path = "/v1/api/userStationList"
        
        # Construct an auth header
        headers = self.doAuth(self.config['api_id'], self.config['api_secret'], req_path, req_body)
                
        self.printDebug(f'Built request - Headers {headers}, body: {req_body}, path: {req_path}')
               
        # Place the request
        r = self.postRequest(
            f"{self.config['api_url']}{req_path}",
            headers,
            req_body
            )
        
        resp = r.json()
        self.printDebug(f'Got station list: {resp}')
        
        return resp


    def postRequest(self, url, headers, data):
        ''' Place a request to the API, taking into account
         internal rate-limit tracking
        '''
        
        # Check whether this request would hit the service's published rate-limit
        x = 0
        while True:
            if self.checkRateLimit():
                # We're below the rate limit, break out
                # so the request can be placed
                break
                
            # Otherwise, this request would hit the rate limit wait a bit and try again
            x += 1
            time.sleep(1)
            if x > self.config("max_ratelimit_wait"):
                self.printDebug("Max ratelimit wait exceeded - something's gone wrong, please report it")
                sys.exit(1)
            continue
        
        # Place the request
        return self.session.post(url=url, headers=headers, data=data)
        

    def printDebug(self, msg):
        if self.debug:
            print(msg)
        


# Utility functions to help with __main__ runs

def configFromEnv():
    ''' Build a dict of configuration settings based on environment variables
    '''
    return {
        "api_id" : int(os.getenv("API_ID", 1234)),
        "api_secret" : os.getenv("API_SECRET", "abcde"),
        "api_url" : os.getenv("API_URL", "https://tobeconfirmed").strip('/'),
        # Max number of requests per 5 seconds
        "api_rate_limit" : int(os.getenv("API_RATE_LIMIT", 3)),
        # This is a safety net - maximum seconds to wait if we believe we'll
        # hit the rate limit. As long as this is higher than api_rate_limit it
        # should never actually be hit unless there's a bug.
        "max_ratelimit_wait" : int(os.getenv("API_RATE_LIMIT_MAXWAIT", 8)),
        "measurement" : os.getenv("MEASUREMENT", "solar_inverter")
        }

def extractBatteryStats(inverter, config):
    ''' Take inverter details and construct line protocol relating to the attached battery
    
    '''

    # TODO: it's not clear whether the API will change units
    # we should probably normalise our output if it does
    
    # tags first 
    tags = {
        "type" : "device",
        "device_type" : "battery",
        "inverter_id" : inverter['id'],
        "inverter_sn" : inverter['sn'],
        "station" : inverter['stationId'],
        "userId" : inverter['userId'],
        "batteryType" : inverter["batteryType"].replace(" ","\\ "),
        "influxdb_database" : "Systemstats"
    }
    
    fields = {
        "batteryPowerUnit" : f'"{inverter["batteryPowerStr"]}"',
        "batteryPowerPerc" : float(inverter['batteryCapacitySoc']),
        "batteryCurrentStr" : f'"{inverter["storageBatteryCurrentStr"]}"',
        "batteryTodayChargeEnergy": float(inverter['batteryTodayChargeEnergy']),
        "batteryTodayChargeEnergyStr": f'"{inverter["batteryTodayChargeEnergyStr"]}"',
        "batteryTodayDischargeEnergy": float(inverter['batteryTodayDischargeEnergy']),
        "batteryTodayDischargeEnergyStr": f'"{inverter["batteryTodayDischargeEnergyStr"]}"',
        "readingAge" : f"{round(time.time() - (int(inverter['dataTimestamp'])/1000))}i",

        }
    

    
    if inverter["batteryPower"] < 0:
        tags["batteryState"] = "discharging"
        fields["batteryDischargeRate"] = float(inverter['batteryPower']) * -1
        fields["batteryChargeRate"] = float(0)
        fields["batteryCurrent"] =  float(inverter['storageBatteryCurrent']) * -1
    else:
        tags["batteryState"] = "charging"
        fields["batteryChargeRate"] = float(inverter['batteryPower'])
        fields["batteryDischargeRate"] = float(0)
        fields["batteryCurrent"] =  float(inverter['storageBatteryCurrent'])
        
    
    # Construct the LP
    lp1 = [config['measurement']]
    for tag in tags:
        lp1.append(f"{tag}={tags[tag]}")
    
    lp2 = []
    for field in fields:
        lp2.append(f"{field}={fields[field]}")
        
    lp = " ".join([
        ','.join(lp1),
        ','.join(lp2)
        ])
    return lp
    

def extractInverterStats(inverter, config):
    ''' Receive a dict of inverter detail and extract inverter details
    
    '''
    # TODO: it's not clear whether the API will change units
    # we should probably normalise our output if it does
        
    # tags first 
    tags = {
        "type" : "device",
        "device_type" : "inverter",
        "inverter_id" : inverter['id'],
        "inverter_sn" : inverter['sn'],
        "station" : inverter['stationId'],
        "userId" : inverter['userId'],
        "inverter_model" : inverter['model'].replace(" ","\ "),
        "influxdb_database" : "Systemstats"        
        
    }
    
    fields = {
        "state" : int(inverter['currentState']),
        "todayYield" : float(inverter['eToday']),
        "todayYieldStr" : f'"{inverter["eTodayStr"]}"',
        "power_ac" : float(inverter['pac']),
        "power_ac_str" : f'"{inverter["pacStr"]}"',
        "temperature" : float(inverter['inverterTemperature']), 
        "gridBuyToday" : float(inverter['gridPurchasedTodayEnergy']),
        "gridSellToday" : float(inverter['gridSellTodayEnergy']),
        "batterySupplyToday" : float(inverter['batteryTodayDischargeEnergy']),
        "batteryChargeToday" : float(inverter['batteryTodayChargeEnergy']),
        "readingAge" : f"{round(time.time() - (int(inverter['dataTimestamp']) / 1000))}i"
        }
    
    
    for i in range(32):
        k = f"pow{i}"
        if k in inverter:
            fields[f"panel_{i}"] = float(inverter[f"pow{i}"])    

    # Total is solar yield + battery output + grid supply
    
    '''
    There's a problem here with the API's output
    
    'gridPurchasedTodayEnergy': 654.6, 'gridPurchasedTodayEnergyStr': 'kWh'
    
    There's no way that we've pulled 654 kWh from the grid. The soliscloud UI says 0.12kWh which doesn't line up either.  
    
    It looks like the API reports in Wh if the value's low enough, but doesn't adjust the unit in the "Str" field. That doesn't do much to explain the different value in the UI though.
    '''
    total_usage = (fields["gridBuyToday"] + fields["batterySupplyToday"] + fields["todayYield"])
    # subtract any power used to charge the battery
    total_usage = total_usage - fields["batteryChargeToday"]
    # and subtract anything shipped back to the grid
    
    # TODO: enable this once the issues above are resolved
    # fields['todayUsage'] = total_usage - fields["gridSellToday"]
    
    # Construct the LP
    lp1 = [config['measurement']]
    for tag in tags:
        lp1.append(f"{tag}={tags[tag]}")
    
    lp2 = []
    for field in fields:
        lp2.append(f"{field}={fields[field]}")
        
    lp = " ".join([
        ','.join(lp1),
        ','.join(lp2)
        ])
    return lp    
    
def extractSiteStats(site, config):
    ''' Receive a dict with a site's details and extract stats
    '''
    # TODO: it's not clear whether the API will change units
    # we should probably normalise our output if it does
    
    # tags first 
    tags = {
        "type" : "site",
        "device_type" : "none",
        "station" : site['id'],
        "userId" : site['userId'],       
    }
    
    fields = {
        "readingAge" : f"{round(time.time() - int(inverter['dataTimestamp']))}i",
        "capacity" : float(site['capacity']),
        "capacityStr" : f'"{site["capacityStr"]}"',
        "dayEnergy" : float(site['dayEnergy']),
        "dayEnergyStr" : f'"{site["dayEnergyStr"]}"',
        "dayIncome" : float(site['dayIncome']),
        }    
    
    
    

if __name__ == "__main__":
    # Are we running in debug mode?
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    config = configFromEnv()    
    soliscloud = SolisCloud(config, debug=DEBUG)
    
    stations = soliscloud.fetchStationList()

    # TODO: lets not do this:
    if not stations or "data" not in stations or "page" not in stations['data'] or "records" not in stations['data']['page']:
        sys.exit(1)
    
    
    # Line protocol will be written into here as it's generated
    lp_buffer = []
    
    # Now get a list of inverters
    for station in stations["data"]["page"]["records"]:
        
        # Get a list of inverters at the station
        inverters = soliscloud.fetchInverterList(station_id=station['id'])
        
        # The list detail doesn't tell us anything about batteries, so we need
        # to iterate through and get details
        if not inverters or "data" not in inverters or "page" not in inverters['data'] or "records" not in inverters['data']['page']:
            # TODO: do we _really_ want to exit at this point, or should we return
            # what we've got?
            sys.exit(1)
            
        for inverter in inverters['data']['page']['records']:
            #print(inverter)
            inverter_details = soliscloud.fetchInverterDetail(inverter['id'])['data']
            lp = extractBatteryStats(inverter_details, config)
            inverter_lp = extractInverterStats(inverter_details, config)
            
            lp_buffer.append(lp)
            lp_buffer.append(inverter_lp)

for line in lp_buffer:
    print(line)
