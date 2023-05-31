### Soliscloud Telegraf Plugin

This is an exec based plugin for Telegraf designed to collect Electricity usage and generation statistics from [Soliscloud](https://www.soliscloud.com/). Inverters, Dataloggers, EPMs and Meters made by [Ginlong Technologies](https://www.ginlong.com/) tend to report  into Soliscloud.

This plugin calls the Soliscloud API in order to retrieve information so that [Telegraf](https://github.com/influxdata/telegraf) can write it into InfluxDB.

More information on the original development can be found in [utilities/telegraf-plugins#9](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/9.html)


----

### Dependencies

* Python >= 3
* Python Requests Module

----

### Pre-Requisites

You will need API access, but this is not enabled by default.

As [detailed here](https://solis-service.solisinverters.com/support/solutions/articles/44002212561-api-access-soliscloud) you'll need to raise a support ticket requesting access (mine was acted on promptly).

Once API access has been enabled for your account, instructions will be given on how to generate credentials. This will result in you having

* An API domain 
* An API Key ID 
* An API Secret



----

### Telegraf Config

The API details can be passed via the `environment` configuration option

```ini
[[inputs.exec]]
    commands = [
        "/usr/local/src/telegraf_plugins/soliscloud.py",
    ]
    timeout = "60s"
    interval = "5m"
    name_suffix = ""
    data_format = "influx"
    environment = [
    "API_ID=",
    "API_SECRET=",
    "API_URL=https://www.soliscloud.com:13333"    
    ]
```


----

### License

Copyright 2023, B Tasker. Released under [BSD 3 Clause](https://www.bentasker.co.uk/pages/licenses/bsd-3-clause.html).
