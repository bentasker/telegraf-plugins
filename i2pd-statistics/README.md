### i2pd Telegraf Plugin

This is an exec based plugin for Telegraf designed to monitor an [i2pd](https://github.com/PurpleI2P/i2pd) instance. `idpd` is a C++ implementation of the [I2P](https://geti2p.net/en/) client.

My website is now [available as an eepsite](https://www.bentasker.co.uk/posts/blog/privacy/bentaskercouk-now-available-on-i2p.html) and I wanted to be able to monitor the daemon.



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


### Example Line Protocol

    i2pd,url=http://localhost:7070,version=2.41.0,network_status=Firewalled,network_status_v6=disabled uptime=73070i,tunnel_creation_success_rate=66,in_bytes=89758106i,in_avg_bps=10977.28,out_bytes=79964406i,out_avg_bps=10158.08,transit_bytes=0i,transit_avg_bps=0.0,routers=1294i,floodfills=814i,leasesets=0i,clienttunnels=32i,transittunnels=0i,inbound_tunnel_count=16i,inbound_tunnels_expiring=4i,inbound_tunnels_established=16i,inbound_tunnels_exploratory=0i,inbound_tunnels_building=0i,inbound_tunnels_failed=0i,outbound_tunnel_count=16i,outbound_tunnels_expiring=4i,outbound_tunnels_established=15i,outbound_tunnels_exploratory=0i,outbound_tunnels_building=0i,outbound_tunnels_failed=0i

----

### License

Copyright 2022, B Tasker. Released under [BSD 3 Clause](LICENSE).
