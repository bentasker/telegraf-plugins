# Tor Daemon Plugin

An `exec` plugin that connects to the Tor Daemon's [control port](https://github.com/torproject/torspec/blob/main/control-spec.txt) to retrieve stats about the daemon's operation.

Design and tracking is under [utilities/telegraf-plugins#1](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/1.html)

An example of using it can be [found on my site](https://www.bentasker.co.uk/posts/documentation/general/monitoring-tor-daemon-with-telegraf.html).

----

### Tor Setup

First, ControlPort needs to be enabled on tor. This script uses hashed password authentication.

Have tor hash your password

    tor --hash-password SecretPass
    
This will return a string of the format

    16:20F64DD23B8043966023A8797DDE0DE3AC697FD8461C1E7B25FF767D47
    
Edit your `torrc` file to enable the control port and set the password

    printf "ControlPort 9051\nHashedControlPassword 16:20F64DD23B8043966023A8797DDE0DE3AC697FD8461C1E7B25FF767D47" | sudo tee -a /etc/tor/torrc

Restart tor

    systemctl restart tor
    
----

### Script Configuration

Take a copy of `tor-daemon.py` and put it somewhere on your server (I use `/usr/local/bin`)

Edit the top of the script to set the correct port and password (in future you should be able to do this in Telegraf's config instead)

    CONTROL_H = os.getenv("CONTROL_HOST", "127.0.0.1")
    CONTROL_P = int(os.getenv("CONTROL_PORT", 9051))
    AUTH = os.getenv("CONTROL_AUTH", "MySecretPass")
    MEASUREMENT = os.getenv("MEASUREMENT", "tor")

----

### Configuring in Telegraf
   
Edit telegraf's configuration to enable the plugin (remember to correct the path if you changed it)

    [[inputs.exec]]
    commands = ["/usr/local/bin/tor-daemon.py"]
    data_format = "influx"

Restart telegraf

    systemctl restart telegraf
    
----

### Tags

The plugin creates the following tags

- `controlport_connection`: did we manage to use the controlport? success/failed
- `network_liveness`: [tor's assessment](https://github.com/torproject/torspec/blob/main/control-spec.txt#L1127) of whether there's network connectivity. up/down
- `version_status`: [tor's assessment](https://github.com/torproject/torspec/blob/main/control-spec.txt#L988) of the currently running tor verion. new,old,unrecommended,recommended,new in series,obsolete,unknown
- `accounting_enabled`: Is accounting enabled
- `accounting_hibernating_state`: (only present if accounting enabled). One of `awake`,`hard`,`soft`


----

### Fields

- `accounting_bytes_read`: number of bytes read/received in this accounting period
- `accounting_bytes_write`: number of bytes written/sent in this accounting period
- `accounting_bytes_remaining_read`: number of bytes left to be read/received in this accounting period
- `accounting_bytes_remaining_write`: number of bytes left to be written/sent in this accounting period
- `accounting_period_length`: Length in seconds of the accounting period
- `accounting_period_seconds_elapsed`: seconds elapsed since the start of the current accounting period
- `accounting_period_seconds_remaining`: seconds remaining in the current accounting period
- `bytes_rx`: bytes received since last daemon restart
- `bytes_tx`: bytes transmitted since last daemon restart
- `dirport_reachability`: 1/0 - [Tor's assessment](https://github.com/torproject/torspec/blob/main/control-spec.txt#L972) of dirport reachibility
- `dormant`: is Tor dormant? 1 if so.
- `guards_down`: number of guards in guardlist considered down
- `guards_never_connected`: number of guards in guardlist we've never connected to
- `guards_total`: number of guards in guardlist
- `guards_unlisted`: number of guards in guardlist considered unlisted
- `guards_unusable`: number of guards in guardlist considered unusable
- `guards_up`: number of guards in guardlist considered up
- `orport_reachability`: 1/0 - [Tor's assessment](https://github.com/torproject/torspec/blob/main/control-spec.txt#L970) of ORport reachibility
- `stats_fetch_failures`: How many stats did the plugin fail to fetch?
- `tor_version`: current tor version string
- `uptime`: seconds since last daemon restart

For relays/exit nodes:

- `ipv4_exit_policy_num_total`: Total number of exit policies
- `ipv4_exit_policy_num_accept`: Total number of accept exit policies 
- `ipv4_exit_policy_num_reject`: Total number of reject exit policies 
- `ipv4_exit_policy_num_wildcard`: Total number of policies that use a `*` for host
- `ipv4_exit_policy_num_specific`: Total number of exit policies that refer to a specific host
- `ipv4_exit_policy_num_unique_hosts`: Number of unique hosts in exit policies
- `ipv4_exit_policy_num_unique_ports`: Number of unique ports in exit policies
- `ipv4_exit_policy_num_wildcard_port`: Number of policies with wildcarded ports
- `ipv4_exit_policy_num_specific_port`: Number of policies mentioning specific ports
- `ipv4_exit_policy_num_port_range`: Number of policies specifying a range of ports
- `ipv4_wildcard_accept` : How many accept policies use wildcards
- `ipv4_specific_accept` : How many accept policies specify specific hosts/networks
- `ipv4_wildcard_port_accept` : How many accept policies use wildcard for ports
- `ipv4_specific_port_accept`: How many accept policies specify specific ports
- `ipv4_unique_hosts_accept` : Number of unique hosts in accept policies
- `ipv4_unique_ports_accept` : Number of unique hosts in accept policies
- `ipv4_wildcard_reject` : How many reject policies use wildcards
- `ipv4_specific_reject` : How many reject policies specify specific hosts/networks
- `ipv4_wildcard_port_reject` : How many reject policies use wildcard for ports
- `ipv4_specific_port_reject`: How many reject policies specify specific ports
- `ipv4_unique_hosts_reject` : Number of unique hosts in reject policies
- `ipv4_unique_ports_reject` : Number of unique hosts in reject policies
- `ipv6_exit_policy_num_total`: Total number of exit policies
- `ipv6_exit_policy_num_accept`: Total number of accept exit policies 
- `ipv6_exit_policy_num_reject`: Total number of reject exit policies 
- `ipv6_exit_policy_num_wildcard`: Total number of policies that use a `*` for host
- `ipv6_exit_policy_num_specific`: Total number of exit policies that refer to a specific host
- `ipv6_exit_policy_num_unique_hosts`: Number of unique hosts in exit policies
- `ipv6_exit_policy_num_unique_ports`: Number of unique ports in exit policies
- `ipv6_exit_policy_num_wildcard_port`: Number of policies with wildcarded ports
- `ipv6_exit_policy_num_specific_port`: Number of policies mentioning specific port
- `ipv6_exit_policy_num_port_range`: Number of policies specifying a range of ports
- `ipv6_wildcard_accept` : How many accept policies use wildcards
- `ipv6_specific_accept` : How many accept policies specify specific hosts/networks
- `ipv6_wildcard_port_accept` : How many accept policies use wildcard for ports
- `ipv6_specific_port_accept`: How many accept policies specify specific ports
- `ipv6_unique_hosts_accept` : Number of unique hosts in accept policies
- `ipv6_unique_ports_accept` : Number of unique hosts in accept policies
- `ipv6_wildcard_reject` : How many reject policies use wildcards
- `ipv6_specific_reject` : How many reject policies specify specific hosts/networks
- `ipv6_wildcard_port_reject` : How many reject policies use wildcard for ports
- `ipv6_specific_port_reject`: How many reject policies specify specific ports
- `ipv6_unique_hosts_reject` : Number of unique hosts in reject policies
- `ipv6_unique_ports_reject` : Number of unique hosts in reject policies


----

### Line Protocol Example

Example output:

```
tor,controlport_connection=success,version_status=recommended,network_liveness=up stats_fetch_failures=0i,bytes_rx=239214179i,bytes_rx=280990655i,uptime=35874i,tor_version="0.4.5.10",dormant=0i,orport_reachability=1i,dirport_reachability=1i,guards_never_connected=22i,guards_down=0i,guards_up=0i,guards_unlisted=0i,guards_unusable=0i,guards_total=22i
tor,controlport_connection=failed,failure_type=connection stats_fetch_failures=1i
tor,controlport_connection=failed,failure_type=authentication stats_fetch_failures=1i
```

----

### Copyright

Copyright (c) 2022 [Ben Tasker](https://www.bentasker.co.uk/)

Released under [GNU GPL V3](https://www.gnu.org/licenses/gpl-3.0.txt)
