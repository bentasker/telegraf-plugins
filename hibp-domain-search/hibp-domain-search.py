#!/usr/bin/env python3
#
# Place a request to the HaveIBeenPwned API to check how many breach records exist for emails under a domain
#

'''
Copyright (c) 2024 B Tasker

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


import os
import requests
import sys

API_KEY=os.getenv("HIBP_TOKEN", False) # Get this from https://haveibeenpwned.com/API/Key
DOMAIN=os.getenv("HIBP_SEARCH_DOMAIN", False) # the domain to search HIBP for

BASE_URL=os.getenv("HIBP_API_URL", "https://haveibeenpwned.com/api/v3")

# Measurement name to use in Influxdb
MEASUREMENT_NAME=os.getenv("INFLUXBD_MEASUREMENT", "hibp_domain_search")


def placeRequest(path):
    ''' Place a request against the UptimeRobot API and return a dict
    '''
    headers = {
        'hibp-api-key': API_KEY
    }
    r = requests.get("{}{}".format(BASE_URL, path), headers=headers)
    
    if r.status_code == 429:
        print("Received a rate-limiting response - you're probably running the plugin too regularly")
        sys.exit(1)
        
    if r.status_code != 200:
        print("An unspecified error occurred")
        print(r.text)
        sys.exit(1)
        
    return r.json()


def writeMailBoxLP(m):
    ''' Convert a mailbox object to line protocol and print it
    '''
    tagset="by=email,email={},search_domain={},mbox={}".format(m["email"], DOMAIN, m['mbox'])
    print("{},{} count={}i".format(MEASUREMENT_NAME, tagset, m["hits"]))


def writePwnedStats(p):
    ''' Write Line protocol about a pwned service
    '''
    tagset="by=pwned_site,service={},search_domain={}".format(p['name'], DOMAIN)
    emails = ','.join(p['mailboxes'])
    count = len(p['mailboxes'])

    print('{},{} count={}i,emails="{}"'.format(MEASUREMENT_NAME, tagset, count, emails))


if __name__ == '__main__':    

    if not all([API_KEY, DOMAIN, BASE_URL]):
        print("You must define environment vars HIBP_TOKEN and HIBP_SEARCH_DOMAIN")
        sys.exit(1)

    hits = placeRequest("/breacheddomain/{}".format(DOMAIN))
    #hits = placeRequestMock("/breacheddomain/{}".format(DOMAIN))

    # Process the response
    #
    # Each top level attribute is a mailbox name under DOMAIN
    pwned_sites = {}
    for mailbox in hits:
        email = "{}@{}".format(mailbox, DOMAIN)
        m = {
            "email": email,
            "mbox": mailbox,
            "hits" : len(hits[mailbox])
        }
        
        writeMailBoxLP(m)
        
        # Update the mapping of pwned sites
        for pwned in hits[mailbox]:
            if pwned not in pwned_sites:
                pwned_sites[pwned] = {
                        "name" : pwned,
                        "mailboxes": []
                    }
            # Append this mailbox to it
            pwned_sites[pwned]["mailboxes"].append(email)


    # Iterate through the collected site names and write details on those
    for pwned in pwned_sites:
        writePwnedStats(pwned_sites[pwned])
