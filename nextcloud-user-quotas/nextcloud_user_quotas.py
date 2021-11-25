#!/usr/bin/env python3
#
# Telegraf Exec plugin to monitor nextcloud user quota usage
#
# Copyright (c) 2021 B Tasker
#
import base64
import requests
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
    return r.json()
    
    
    
    
def getUserList():
    ''' Get a list of users
    
    '''
    resp_json = makeRequest('/users')   
    return resp_json['ocs']['data']['users']
        
    
    
def getUserInfo(user):
    ''' Fetch info from the API for a username
    
    '''
    userinfo = makeRequest(f'/users/{user}')
    
    if userinfo['ocs']['data']['quota']['quota'] < 0:
        # Unlimited
        userinfo['ocs']['data']['quota']['quota'] = 0
        userinfo['ocs']['data']['quota']['relative'] = 0.00
    
    return userinfo['ocs']['data']['quota']
    

def quota_to_lp(user, quota_obj):
    ''' Take a quota object and output Influx line protocol
    
    '''
    return f"{MEASUREMENT},user={user},hostname={NEXTCLOUD_DOMAIN} quota={quota_obj['quota']}i,free={quota_obj['free']}i,used={quota_obj['used']}i,percent_used={quota_obj['relative']} {TIMESTAMP}"



def main():
    ''' Main entrypoint
    
    '''
    users = getUserList()
    for user in users:
        quota_obj = getUserInfo(user)
        lp = quota_to_lp(user, quota_obj)
        print(lp)
    


# Work starts
SESSION=requests.session()
TIMESTAMP=int(time.time()*1000000000) # we use int to prevent an exponent from being used
ENCODED_AUTH=base64.b64encode(bytes(NEXTCLOUD_PASS,'utf-8')).decode()

# Trigger the app
main()
