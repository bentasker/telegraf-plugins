# BunnyCDN Telegraf exec plugin

An `exec` plugin for Telegraf to poll the [BunnyCDN](https://bunny.net) API and retrieve stats for properties served through their CDN.

By default, this will write into a measurement called `bunnycdn` - you can change this at the head of the script.


### Stats collected

The following stats are extracted from the API

- Request Hit Ratio (`RHR`)
- Bytes served at the edge (`edge_bytes`)
- Average origin response time (`mean_origin_response_time`)
- Average Request Hit Ratio (`mean_rhr`)
- Bytes served by origin (`origin_bytes`)
- Origin Response time (`origin_response_time`)
- Number of requests served (`requests_served`)
- Requests with 3xx status (`status_3xx`)
- Requests with 4xx status (`status_4xx`)
- Requests with 5xx status (`status_5xx`)
- Total bandwidth used (`total_bandwidth_used`)
- Total origin traffic (`total_origin_traffic`)
- Total Requests served (`total_requests_served`)

### Setup

Configure in telegraf as follows

```
[[inputs.exec]]
  commands = [
    "/usr/local/src/telegraf_plugins/bunny-cdn-stats.py [API_KEY]",
  ]
  timeout = "60s"
  interval = "15m"
  name_suffix = ""
  data_format = "influx"
```

Replacing `[API_KEY]` with your BunnyCDN API Key (visible under "My Account")

---

### Copyright

Copyright (c) 2021 [Ben Tasker](https://www.bentasker.co.uk)

Released under [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.txt)
