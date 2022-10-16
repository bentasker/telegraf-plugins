# Tor Snowflake Plugin for Telegraf


This `exec` plugin for [Telegraf](https://github.com/influxdata/telegraf) collects basic stats from [Tor's Snowflake](https://snowflake.torproject.org/), showing how many connections have been handled, and how much data sent.

The most common means of running Snowflake on a server is with docker, so this plugin assumes that's what you've done (if you are running directly, you should just need to replace the `docker` call with a `journalctl` call - depending on how you've configured logging)

----

### Setup

The user that Telegraf runs as will need permission to invoke `docker`, the official Docker plugin [has instructions on configuring permissions](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/docker#docker-daemon-permissions).

You'll need to save `tor-snowflake.sh` somewhere that Telegraf can access, and make it executable

    mkdir -p /usr/local/src/telegraf_plugins/
    cd /usr/local/src/telegraf_plugins/
    wget https://raw.githubusercontent.com/bentasker/telegraf-plugins/master/tor-snowflake/tor-snowflake.sh
    chmod +x /usr/local/src/telegraf_plugins/tor-snowflake.sh
    
Then add an `exec` section to your Telegraf configuration

    [[inputs.exec]]
        environment = [
            "MEASUREMENT=snowflake",
            "LOG_PERIOD=4h",
            "CONTAINER=snowflake-proxy"
            ]
            
        commands = [
            "/usr/local/src/telegraf_plugins/tor-snowflake.sh",
        ]
        timeout = "60s"
        interval = "15m"
        name_suffix = ""
        data_format = "influx"
        
Then restart telegraf

    systemctl restart telegraf
    
----

### Additional Configuration

The plugin can be configured via environment variables - since

