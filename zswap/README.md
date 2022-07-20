# zswap Plugin

An `exec` plugin intended to collect statistics about usage of the Linux Kernel's [`zswap` pool](https://www.kernel.org/doc/html/latest/admin-guide/mm/zswap.html)

An example of using the statistics can be found in [Enabling and monitoring the zswap compressed page cache on Linux](https://www.bentasker.co.uk/posts/documentation/linux/enabling-and-monitoring-zswap-compressed-swap-on-linux.html#telegraf_exec_script).

----

### Installation and Setup

The plugin relies on the `debugfs` filesystem, which (on most systems) is only available to `root`. 

Save `zswap.sh` onto your system (I save to `/usr/local/src`)

If telegraf isn't running as root, it'll need to be able to invoke `sudo` when calling the plugin.
```sh
echo "telegraf ALL = NOPASSWD: /usr/local/src/zswap.sh" | sudo tee /etc/sudoers.d/telegraf_zswap
chmod -w /usr/local/src/zswap.sh
sudo chown root /usr/local/src/zswap.sh
```

Then it's just a case of adding an `exec` section to telegraf's config file
```
[[inputs.exec]]
  commands = ["sudo /usr/local/src/zswap.sh"]
  data_format = "influx"
```

----

### Graphing

[My post](https://www.bentasker.co.uk/posts/documentation/linux/enabling-and-monitoring-zswap-compressed-swap-on-linux.html#query_statistics) gives examples of querying and calculating useful stats.

Chronograf users can also import the dashboard defined in [`zswap.json`](zswap.json)

----

### Tags

The plugin currently creates the following tags

* enabled
* compressor
* same_filled_pages_enabled
* zpool

----

### Fields

* duplicate_entry
* pool_limit_hit
* pool_total_size
* reject_alloc_fail
* reject_compress_poor
* reject_kmemcache_fail
* reject_reclaim_fail
* same_filled_pages
* stored_pages
* written_back_pages
* accept_threshold_percent
* max_pool_percent
* page_size

----

### Line Protocol Example

    zswap,enabled=Y,compressor=lzo,same_filled_pages_enabled=Y,zpool=zbud duplicate_entry=0,pool_limit_hit=0,pool_total_size=673927168,reject_alloc_fail=0,reject_compress_poor=17203,reject_kmemcache_fail=0,reject_reclaim_fail=0,same_filled_pages=43367,stored_pages=307492,written_back_pages=0,accept_threshold_percent=90,max_pool_percent=20,page_size=4096

----

### Copyright

Copyright (c) 2022 Ben Tasker

Released under [GNU GPL V3](https://www.gnu.org/licenses/gpl-3.0.txt)
