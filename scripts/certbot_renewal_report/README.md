# Certbot Renewal Report Script

This script is a `post-deploy` hook for [`certbot`](https://certbot.eff.org/).

It's fired when certbot successfully acquires or renews a certificate and will push metrics into [InfluxDB](github.com/influxdata/influxdb) indicating which domains were renewed.

This can then be used to develop alerting and give an early alert if a certificate has not been renewed within a desirable time-range


----

### Setup

Setup is simple, ensure that you've got the dependencies

    apt-get install python3-requests
    
Drop a copy of the script into `/etc/letsencrypt/renewal-hooks/deploy`

Make it executable

    chmod +x /etc/letsencrypt/renewal-hooks/deploy/certbot_renewal_report.py
    
And move onto configuring

----

### Configuration

There are a number of variables that need setting. The easiest way to do so is to edit the top of the script

    # Measurement name to use in InfluxDB
    measurement = os.getenv("MEASUREMENT", "certbot_renewal")
    
    # System hostname
    host = os.getenv("HOSTNAME", os.uname()[1])
    
    # URL to InfluxDB
    influx_url = os.getenv("INFLUXDB_URL", "http://127.0.0.1:8086")
    
    # Token, empty or username:password
    influx_token = os.getenv("INFLUXDB_TOKEN", "")
    
    # Major version of InfluxDB in use
    influx_ver = os.getenv("INFLUXDB_USER", "2") # or 1 for 1.x
    
    # Database/bucket name
    influx_bucket = os.getenv("INFLUXDB_BUCKET", "telegraf")
    
Alternatively, you can ensure these values are exported into the environment that certbot is running in.

-----

### Metrics

Tags:

- `host`: hostname of the system running the script
- `domain`: domain cert was acquired for (or `all` for the global stat)

Fields

- `renewed_count`: how many certificates were renewed for this series?


----

### Line Protocol Example

```
certbot_renewal,domain=all,host=optimus renewed_count=2 1656169934438253518
certbot_renewal,domain=foo.example.com,host=optimus renewed_count=1 1656169934438253518
certbot_renewal,domain=bar.example.xyz,host=optimus renewed_count=1 1656169934438253518
```

----

### Copyright

Copyright (c) 2022 [Ben Tasker](https://www.bentasker.co.uk/)

Released under [GNU GPL V3](https://www.gnu.org/licenses/gpl-3.0.txt)
