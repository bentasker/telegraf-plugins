#!/bin/bash
#
#
# Version 0.1
#
#


# Space seperated list of block device names
DEVICES=${DEVICES:-"sda"}

# Command to use to invoke smartctl
SMARTCTL=${SMARTCTL:-"sudo smartctl"}

function get_remaining_percentage(){
    device=$1
    cmd_op=`$SMARTCTL -A $device`
    echo "${cmd_op}" | grep -q "Percentage Used:"
    if [ "$?" == "0" ]
    then
        # New format
        usage=`echo "${cmd_op}" | grep "Percentage Used:" | awk '{print $NF}' | tr -d '%'`
        remaining=$(( 100 - $usage ))
        echo "$remaining"
        return
    fi

    echo "${cmd_op}" | egrep -q "Percent_Lifetime_Remain|Wear_Leveling_Count"
    if [ "$?" == "0" ]
    then
        usage=`echo "${cmd_op}" | egrep "Percent_Lifetime_Remain|Wear_Leveling_Count" | awk '{print $4}'`
        # Strip any leading 0s by converting from base10 to base10
        remaining=$((10#$usage))
        echo "$remaining"
        return
    fi
}


# Iterate over the configured devices
for device in $DEVICES
do
    if [ ! -e /dev/$device ]
    then
        # Device doesn't exist
        continue
    fi

    lifetime=`get_remaining_percentage /dev/$device`
    if [ "$lifetime" == "" ]
    then
        # Couldn't get a result, skip
        continue
    fi
    
    # Otherwise, echo out some lp
    echo "ssd_lifetime,host=$HOSTNAME,device=$device perc_remaining=${lifetime}i"
done
