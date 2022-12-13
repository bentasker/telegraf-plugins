#!/usr/bin/env python3
#
# Call the webmention.io and retrieve recent webmentions
# 
# These are then converted to Line Protocol for writing into InfluxDB
#
# Warning: This generates a high cardinality dataset, you will almost
# certainly want to implement downsampling if you're only interested
# in aggregate stats
#
# pip3 install requests dateparser
#
'''
Copyright (c) 2022 B Tasker

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import datetime as dt
import requests

from dateutil.parser import parse

# The measurement to write mentions into
MEASUREMENT = "webmentions"

# How far back should we tell the API to search?
MINUTES = 60

# A list of your API tokens, you'll have 1 per site that you've set up
# on webmention.io
TOKENS = [""]

def build_lp(entry):
    ''' Build line protocol to describe the mention
    '''
    
    author = entry['author']['name'].replace(' ', '\ ')
    author_url = entry['author']['url'].replace('"', '')
    
    # Convert time to nanosecond epoch
    do = dt.datetime.strptime(entry['wm-received'], '%Y-%m-%dT%H:%M:%SZ')
    
    if "published" in entry and entry['published']:
        do = parse(entry['published'])
    
    
    mention_date = str(int(do.strftime('%s')) * 1000000000)
    
    # ID and type
    wm_id = entry['wm-id']
    wm_type = entry['wm-property']

    # Linked URL
    url = entry['wm-target'].split("#")[0]

    # Where they linked from
    source_url = entry['url'].replace('"', '')


    # Start putting it all together
    tagset = [
        MEASUREMENT,
        f'type={wm_type}',
        f'url={url}',
        f'author={author}',
        'influxdb_database=webmentions'
              ]
              
    fieldset = [
              f'id={wm_id}',
              f'author_url="{author_url}"',
              f'linked_from="{source_url}"'
              ]
    
    if "content" in entry:
        content = entry['content']['text'][0:1000].replace('"', '').replace('\n', ' ').replace('\r', ' ').replace('\\','\\\\')
        fieldset.append(f'content="{content}"')
    
    # Put it all back together and return
    return ','.join(tagset) + " " + ','.join(fieldset) + f" {mention_date}"
    

def main():
    ''' Call the API and trigger LP generation
    '''
    now = dt.datetime.now()
    d = dt.timedelta(minutes = MINUTES)
    a = now - d
    since = a.strftime('%Y-%m-%dT%H:%M:%SZ')


    for token in TOKENS:
        # Call the API
        r = requests.get(f'https://webmention.io/api/mentions.jf2?token={token}&since={since}')
        d = r.json()

        if "children" not in d:
            continue

        # Iterate over the result
        for entry in d['children']:
            # Print the LP
            print(build_lp(entry))
        

main()
