# Uptime Robot Telegraf Exec Plugin

`exec` plugin to poll [Uptime Robot](https://uptimerobot.com)'s API and retrieve stats for all monitored endpoints.

This'll collect

- Current status
- Average response times


### Setup

You'll need to get an API key (read-only is strongly recommended)

- Go to https://uptimerobot.com/dashboard#mySettings and login
- On the right should be a block for Read-Only API key
- Create one if there isn't already one
- Set it in the head of the exec script


#### Telegraf Config

Configuration in Telegraf is simple - assuming the script `uptime-robot.py` has been saved in `/usr/local/src/telegraf-plugins`:
```
[[inputs.exec]]
  commands = [
    "/usr/local/src/telegraf_plugins/uptime-robot.py",
  ]
  timeout = "60s"
  interval = "5m"
  name_suffix = ""
  data_format = "influx"
```

Note: unless you've got an Uptime-Robot Pro account, there's no point in an interval of < 5m as that's how often the checks run on their end.


---

### Copyright

Copyright (c) 2021 [Ben Tasker](https://www.bentasker.co.uk)
