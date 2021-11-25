## Nextcloud User Quotas Plugin

An `exec` plugin that uses Nextcloud's API in order to retrieve current quota usage for each Nextcloud user - allowing reporting and alarming.


### Nextcloud setup

You will need to create an admin user in Nextcloud for the poller to use.


### Script Configuration

The script has some configuration at the top - it's there to prevent creds showing up in process listing, but could trivially be moved

    NEXTCLOUD_DOMAIN="[domain]"
    NEXTCLOUD_PROTO="https"
    NEXTCLOUD_PASS="[user]:[password]"
    MEASUREMENT="nextcloud_quotas"  

Edit the variables as necessary


### Configuring in Telegraf

Assuming the script has been copied to `/usr/loca/src/telegraf_plugins` the following config can be used in Telegraf

    [[inputs.exec]]
    commands = [
        "/usr/local/src/telegraf_plugins/nextcloud_user_quotas.py",
    ]
    timeout = "5s"
    name_suffix = ""
    data_format = "influx"
  
  
#### Line Protocol example

Example output:

    nextcloud_quotas,user=admin,hostname=nextcloud.example.com quota=0i,free=471037771776i,used=15209524i,percent_used=0.0 1637853522420120064
    nextcloud_quotas,user=ben,hostname=nextcloud.example.com  quota=64424509440i,free=25321839264i,used=39102670176i,percent_used=60.7 1637853522420120064
    nextcloud_quotas,user=telegraf_api_poller,hostname=nextcloud.example.com quota=0i,free=471037771776i,used=22868401i,percent_used=0.0 1637853522420120064
    
    
    
### Graphing

To graph out per user, but exclude specific users, you can use the following Flux

    from(bucket: "telegraf/autogen")
    |> range(start: v.timeRangeStart)
    |> filter(fn: (r) => r._measurement == "nextcloud_quotas" and r._field == "percent_used")
    |> filter(fn: (r) => r.user != "admin" and r.user != "telegraf_api_poller")
    |> aggregateWindow(every: 5m, fn: mean)
    |> keep(columns: ["_time", "user", "_value"])
