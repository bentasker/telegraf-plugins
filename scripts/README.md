# Scripts

Files under this directory aren't written as telegraf `exec` plugins, but collect metrics and write them into InfluxDB (or telegraf via it's influxdb_listener plugin)

Essentially, they're event based scripts that don't fit well into an `exec` or `execd` model
