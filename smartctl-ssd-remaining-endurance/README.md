# SmartCTL SSD Remaining Endurance Exec Plugin for Telegraf

### Background

This `exec` plugin for Telegraf will use `smartctl` to try and collect the remaining endurance for SSDs so that you can generate alerts on any that are getting too low.



### Setup

You'll need `smartmontools` installed

    apt-get install smartmontools
    
The user you run `telegraf` as (usually `telegraf`) will need to be allowed to invoke `smartctl`. The simplest way to do this is to add a sudo permission

    sudo -s
    type -p smartctl # make a note of the path
    visudo 
    telegraf  ALL=(ALL) NOPASSWD:<path from above>

This should give you something like

    telegraf  ALL=(ALL) NOPASSWD:/usr/sbin/smartctl
    
Save and exit
    

    
### Configuration

Save `smartctl-ssd-remaining-endurances.sh` to disk (I tend to use `/usr/local/src/telegraf_plugins`) and then edit the variables at the top.

    # Space seperated list of block device names
    DEVICES=${DEVICES:-"sda"}

    # Command to use to invoke smartctl
    SMARTCTL=${SMARTCTL:-"sudo smartctl"}

ensure that it's executable

    chmod +x /usr/local/src/telegraf_plugins/smartctl-ssd-remaining-endurances.sh
    
Then, add an `exec` section to your telegraf config (replacing the path to the file if you used a different one to me)

    [[inputs.exec]]
    commands = [
        "/usr/local/src/telegraf_plugins/smartctl-ssd-remaining-endurances.sh",
    ]
    timeout = "60s"
    interval = "15m"
    name_suffix = ""
    data_format = "influx"

Then restart telegraf

    systemctl restart telegraf

