#!/bin/bash
#
#

MEASUREMENT=${MEASUREMENT:-"zswap"}

# Get the zswap config
cd /sys/module/zswap/parameters/


# Tags
config_tags=`grep -H . enabled compressor same_filled_pages_enabled zpool | tr ':' '=' | tr '\n' ','`

# Fields
config_fields=`grep -H . accept_threshold_percent max_pool_percent | tr ':' '=' | tr '\n' ','`

# Get the page size
page_size=`getconf PAGESIZE`

# Get current state
cd /sys/kernel/debug/zswap/

# They're all going to be fields, so do it in a one-liner
state=`grep -H . * | tr ':' '=' | tr '\n' ','`


# Put it all together
echo "$MEASUREMENT,${config_tags%,*} ${state}${config_fields}page_size=$page_size"
