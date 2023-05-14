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


class SolisCloud:

    def __init__(self, config, session=False):
        self.config = config
        if session:
            self.session = session
        else:
            self.session = requests.session()

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
        # The entries should be seperated by \n - the API doesn't want
        # literal newlines (presumably it evaluates them on read)
        signstr = '\\n'.join([method,
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
        
        # Job done
        return auth_header


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
        auth_header = self.doAuth(self.config['api_id'], self.config['api_secret'], req_path, req_body)
        
        # Construct headers dict
        headers = {
            "Authorization" : auth_header,
            "Content-Type" : "application/json"
            }
        
        self.printDebug(f'Built request - Headers {headers}, body: {req_body}, path: {req_path}')
        
        # Place the request
        r = self.session.post(
            url = f"{self.config['api_url']}{req_path}", 
            headers = headers,
            data = req_body
            )
        
        return r.json()

    def printDebug(self, msg):
        if DEBUG:
            print(msg)
        


# Utility functions to help with __main__ runs

def configFromEnv():
    ''' Build a dict of configuration settings based on environment variables
    '''
    return {
        "api_id" : int(os.getenv("API_ID", 1234)),
        "api_secret" : os.getenv("API_SECRET", "abcde"),
        "api_url" : os.getenv("API_URL", "https://tobeconfirmed")
        }



if __name__ == "__main__":
    DEBUG = True
    config = configFromEnv()    
    soliscloud = SolisCloud(config)
    
    # These are the example values used in the API doc
    print(soliscloud.doAuth('2424', 
                '668018254', 
                '/v1/api/userStationList', 
                '{"pageNo":1,"pageSize":10}', 
                method="POST", 
                content_type="application/json", 
                datestring='Fri, 26 Jul 2019 06:00:46 GMT')
        )

    stations = soliscloud.fetchStationList()
