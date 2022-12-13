# Webmention.io Telegraf exec plugin

An `exec` plugin for Telegraf to poll the [WebMention.io](https://webmention.io) API and retrieve details of recent webmentions.

By default, this will write into a measurement called `webmentions` - you can change this at the head of the script.

Note that because this plugin is collecting mentions rather than aggregate stats, the resulting data can be quite high cardinality: you may want to downsample for long term storage.

----

### Tags

* `type`: The webmention type (`in-reply-to`, `like-of`, `repost-of`, `bookmark-of`, `mention-of`, `rsvp`, `follow-of`)
* `url`: The URL that the mention references (i.e. the URL on your site)
* `author`: The author of the mention

----

### Fields

* `id`: The webmention.io ID for this mention
* `author_url`: The URL of the author's profile (where available)
* `linked_from`: Where the mention was made
* `content`: Where the mention is text based (like `in-reply-to`), the first 1000 chars of the comment/reply

----

### Dependencies

You will need two python modules
```
pip3 install requests dateparser
```

----

### Configuration

There are 3 variables at the top of the script
```python
# The measurement to write mentions into
MEASUREMENT = "webmentions"

# How far back should we tell the API to search?
MINUTES = 60

# A list of your API tokens, you'll have 1 per site that you've set up
# on webmention.io
TOKENS = [""]
```

You'll need to log into `webmention.io` and grab your API token from the settings page. If you've got multiple domains configured with `webmention.io` you can provide multiple tokens:
```python
TOKENS = ["abcde", "fghijk"]
```
----

### Setup

Configure in telegraf as follows

```
[[inputs.exec]]
  commands = [
    "/usr/local/src/telegraf_plugins/webmention_io.py",
  ]
  timeout = "60s"
  interval = "15m"
  name_suffix = ""
  data_format = "influx"
```

----

### Routed Output

Because the data is potentially quite high cardinality, you may want to write it into a seperate short-lived database (to then downsample from).

The plugin includes a tag `influxdb_database` so that you can achieve this by having multiple Telegraf outputs and using `tagpass` to control which metrics are written to each.

```
# Main Output
[[outputs.influxdb_v2]]
  urls = ["http://192.168.3.84:8086"]
  bucket = "telegraf"
  token = "abcdefg"
  organization = "1ffffaaaa"
  
  [outputs.influxdb_v2.tagdrop]
    influxdb_database = ["*"]
    
# Webmentions output
[[outputs.influxdb_v2]]
  urls = ["http://127.0.0.1:8086"]
  bucket = "webmentions"
  token = "abcdefg"
  organization = "1ffffaaaa"

  # drop the routing tag
  tagexclude = ["influxdb_database"]
  [outputs.influxdb_v2.tagpass]
    influxdb_database = ["webmentions"]

```

----

### Copyright

Copyright (c) 2022 [Ben Tasker](https://www.bentasker.co.uk)

Released under [MIT License](https://www.bentasker.co.uk/pages/licenses/mit-license.html)
