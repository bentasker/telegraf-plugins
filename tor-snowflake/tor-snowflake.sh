#!/bin/bash
#
# Telegraf exec plugin for Tor Snowflake
#
# Snowflake periodically logs how many connections it's served and how much data was sent
# this plugin collects information from those loglines so that basic stats can be tracked
#
#
# Copyright (c) 2022 B Tasker
# Released under GNU GPL v3 - https://www.gnu.org/licenses/gpl-3.0.txt
#

# Container Name
CONTAINER=${CONTAINER:-"snowflake-proxy"}

# Measurement name to use
MEASUREMENT=${MEASUREMENT:-"snowflake"}

# How many hours of docker logs should we check?
LOG_PERIOD=${LOG_PERIOD:-"4h"}


function unit_to_bytes(){
    # The unit used can vary, convert it back
    #
    # Essentially reversing this
    # https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake/-/blob/main/proxy/lib/util.go#L87
    unit=$1
    val=$2

    case $unit in
        KB)
            val=$(( $val * 1000));;
        MB)
            val=$(( ($val * 1000) * 1000));;
        GB)
            val=$(( (($val * 1000) * 1000) * 1000));;
    esac
    
    echo $val
}


function period_to_s(){
    # Convert a Golang time.Duration string to seconds
    tp=$1
    
    # tp will be something like
    # 4h3m21s
    hours=`echo "$tp" | cut -d 'h' -f1`
    minutes=`echo "$tp" | cut -d 'h' -f2 | cut -d 'm' -f1`
    seconds=`echo "$tp" | cut -d 'h' -f2 | cut -d 'm' -f2 | cut -d 's' -f1`
    
    # convert and sum
    echo $(( $seconds + ($minutes * 60) + ($hours * 3600)))
}


# Retrieve logs from Docker and iterate over the lines
docker logs --since $LOG_PERIOD "$CONTAINER" 2>&1 | grep "In the last" | while read -r line
do
    # Get date from the logline and turn into a timestamp
    d=`echo "$line" | cut -d\  -f1`
    t=`echo "$line" | cut -d\  -f2`
    ts=$((`date --date="$d $t" +'%s'` * 1000000000))

    # Get the time period the counts relate to
    period=`echo "$line" | cut -d\  -f6`

    # Stats
    conns=`echo "$line" | cut -d\  -f9`
    sent=`echo "$line" | cut -d\  -f14`
    rec=`echo "$line" | cut -d\  -f17`

    # The unit used can vary, extract it and then convert
    # the relevant stats
    sent_unit=`echo "$line" | cut -d\  -f15 | tr -d ',.'`
    rec_unit=`echo "$line" | cut -d\  -f18 | tr -d ',.'`

    # Do conversions
    sent=`unit_to_bytes "$sent_unit" "$sent"`
    rec=`unit_to_bytes "$rec_unit" "$rec"`
    time_period=`period_to_s $period`

    # Output Line Protocol
    echo "$MEASUREMENT,timeperiod_s=$time_period conns=${conns}i,sent=${sent}i,recv=${rec}i $ts"
done
