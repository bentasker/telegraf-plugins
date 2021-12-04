#!/usr/bin/env python3
#
# Telegraf Exec plugin to monitor nextcloud user quota usage
#
# Copyright (c) 2021 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#
#
import base64
import requests
import sys
import time

# Config
NEXTCLOUD_DOMAIN=""
NEXTCLOUD_PROTO=""
NEXTCLOUD_PASS=""
MEASUREMENT=""



def makeRequest(path, params=False):
    ''' Place a request to the Nextcloud API
    
    
    '''
    if not params:
        params = {}
        
    params['format'] = "json"
    headers = {
        "Content-Type" : "application/x-www-form-urlencoded",
        "OCS-APIRequest" : "true",
        "Authorization" : f"Basic {ENCODED_AUTH}"
        
        }


    r = SESSION.get(f"{NEXTCLOUD_PROTO}://{NEXTCLOUD_DOMAIN}/ocs/v2.php/cloud/{path}", params=params, headers=headers)
    
    if r.status_code == 200:
        return r.json(), 200
    else:
        return False, r.status_code
    
    
    
def getUserList():
    ''' Get a list of users
    
    '''
    resp_json, stat_code = makeRequest('/users')
    
    if not resp_json:
        return False, stat_code
    
    return resp_json['ocs']['data']['users'], stat_code
        
    
    
def getUserInfo(user):
    ''' Fetch info from the API for a username
    
    '''
    userinfo, stat_code = makeRequest(f'/users/{user}')
    
    if not userinfo:
        return False, stat_code
    
    if userinfo['ocs']['data']['quota']['quota'] < 0:
        # Unlimited
        userinfo['ocs']['data']['quota']['quota'] = 0
        userinfo['ocs']['data']['quota']['relative'] = 0.00
    
    return userinfo['ocs']['data']['quota'], stat_code
    


def quota_to_lp(user, quota_obj):
    ''' Take a quota object and output Influx line protocol
    
    '''
    return f"{MEASUREMENT},user={user},hostname={NEXTCLOUD_DOMAIN} quota={quota_obj['quota']}i,free={quota_obj['free']}i,used={quota_obj['used']}i,percent_used={quota_obj['relative']} {TIMESTAMP}"



def status_to_lp(stat_code, user = False):
    ''' Accept a status code and an optional user and create a line of LP
    
    '''
    if user:
        s = f"{MEASUREMENT},user={user},hostname={NEXTCLOUD_DOMAIN} api_status_code={stat_code} {TIMESTAMP}"    
    else:
        s = f"{MEASUREMENT},user=none,hostname={NEXTCLOUD_DOMAIN} api_status_code={stat_code} {TIMESTAMP}"
    
    return s



def main():
    ''' Main entrypoint
    
    '''
    users, stat_code = getUserList()

    print(status_to_lp(stat_code))    
    if not users:
        # API returned an error
        sys.exit(1)
    
    # Otherwise
    for user in users:
        quota_obj, stat_code = getUserInfo(user)
        
        print(status_to_lp(stat_code, user))        
        if not quota_obj:
            # API returned an error
            # Other users might work though
            continue
        
        lp = quota_to_lp(user, quota_obj)
        print(lp)
    


# Work starts
SESSION=requests.session()
TIMESTAMP=int(time.time()*1000000000) # we use int to prevent an exponent from being used
ENCODED_AUTH=base64.b64encode(bytes(NEXTCLOUD_PASS,'utf-8')).decode()

# Trigger the app
main()
