### i2pd Telegraf Plugin

This is an exec based plugin for Telegraf designed to monitor an [i2pd](https://github.com/PurpleI2P/i2pd) instance. `idpd` is a C++ implementation of the [I2P](https://geti2p.net/en/) client.

My website is now [available as an eepsite](https://www.bentasker.co.uk/posts/blog/privacy/bentaskercouk-now-available-on-i2p.html) and I wanted to be able to monitor the daemon.


----

### Dependencies

* Python >= 3
* Python Requests Module


### Telegraf Config

Assuming the plugin has been saved to `/usr/local/bin`

    [[inputs.exec]]
    commands = ["/usr/local/bin/i2pd-statistics.py"]
    data_format = "influx"
    
### Custom Port

By default, the plugin assumes that I2PD's web console is listening on `localhost:7070`.

If that's not the case, then you can use an environment variable to override it (assuming here it's actually on 8080):

    echo 'I2PD_CONSOLE="http://localhost:8080"' | sudo tee -a /etc/default/telegraf
    
### Custom Measurement

By default, the measurement will be called `i2pd` - if you want to change this then you can do so with environment variable `I2PD_MEASUREMENT`.

    echo 'I2PD_MEASUREMENT="i2pd_stats"' | sudo tee -a /etc/default/telegraf


### Known Limitations

`i2pd` doesn't expose stats in a machine readable format - it [generates html](https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L255) for both the Web interface and the QT based UI.

Stats extraction, then, is inavoidably reliant on screen scraping - so if the way in which stats are presented changes in a later release, this plugin may fail to collect some (or all) stats.

The plugin is also not currently coded particularly defensively - I wanted to get stats collection up and running quickly (so I could move onto building dashboards), with an aim to refactoring later (it also needs some DRY work).

----

### Statistics Collected

**Tags**

* `url`: The URL used to reach the webconsole (basically, the value of `I2PD_CONSOLE`
* `version`: The reported version of `i2pd`
* `network_status`: The reported status of i2pd (values [here](https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L223))
* * `network_status_v6`: The reported status of i2pd for IPv6 (values [here](https://github.com/PurpleI2P/i2pd/blob/openssl/daemon/HTTPServer.cpp#L223))
* `statspage_status`: The status of the page at `url`, one of `available`,`unavailable`


**Fields**

* `uptime`: the uptime reported by the daemon, in seconds
* `tunnel_creation_success_rate`: the percentage success rate of tunnel creation
* `in_bytes` / `out_bytes`: the number of bytes received/sent
* `in_avg_bps` / `out_avg_bps`: the average bitrate in/out
* `transit_bytes`: the number of bytes sent out for transit tunnels
* `transit_avg_bps`: the average transmit rate for transit tunnels
* `routers`: Number of routers
* `floodfills`: Number of floodfills
* `leasesets`: Number of LeaseSets
* `clienttunnels`: Number of client tunnels
* `transittunnels`: Number of Transit tunnels
* `inbound_tunnel_count` / `outbound_tunnel_count`: Total number of tunnels
* `inbound_tunnel_expiring` / `outbound_tunnel_expiring`: Total number of tunnels currently in an expiring state
* `inbound_tunnel_established` / `outbound_tunnel_established`: Total number of tunnels currently in an established state
* `inbound_tunnel_exploratory` / `outbound_tunnel_exploratory`: Total number of tunnels currently in an established but exploratory state
* `inbound_tunnel_building` / `outbound_tunnel_building`: Total number of tunnels currently building
* `inbound_tunnel_failed` / `outbound_tunnel_failed`: Total number of tunnels currently in an failed state

### Example Line Protocol

    i2pd,url=http://localhost:7070,version=2.41.0,network_status=Firewalled,network_status_v6=disabled uptime=73070i,tunnel_creation_success_rate=66,in_bytes=89758106i,in_avg_bps=10977.28,out_bytes=79964406i,out_avg_bps=10158.08,transit_bytes=0i,transit_avg_bps=0.0,routers=1294i,floodfills=814i,leasesets=0i,clienttunnels=32i,transittunnels=0i,inbound_tunnel_count=16i,inbound_tunnels_expiring=4i,inbound_tunnels_established=16i,inbound_tunnels_exploratory=0i,inbound_tunnels_building=0i,inbound_tunnels_failed=0i,outbound_tunnel_count=16i,outbound_tunnels_expiring=4i,outbound_tunnels_established=15i,outbound_tunnels_exploratory=0i,outbound_tunnels_building=0i,outbound_tunnels_failed=0i

----

### License

Copyright 2022, B Tasker. Released under [BSD 3 Clause](LICENSE).
