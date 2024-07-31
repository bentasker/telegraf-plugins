# HaveIBeenPwned Domain Search Telegraf Exec Plugin

`exec` plugin to poll the [HaveIBeenPwned](https://haveibeenpwned.com) [domain search](https://haveibeenpwned.com/API/v3#BreachesForDomain) API to generate stats about observed breaches.


This'll perform a domain search in order to collect

- A list of pwned email addresses
- The breaches that they were identified in


### Setup

You'll need to get an API key (read-only is strongly recommended)

- To have verified the domain on the [domain search dashboard](https://haveibeenpwned.com/DomainSearch)
- An [API Key](https://haveibeenpwned.com/API/Key)


#### Telegraf Config

Configuration in Telegraf is simple - assuming the script `hibp-domain-search.py` has been saved in `/usr/local/src/telegraf-plugins`:
```
[[inputs.exec]]
   # The domain provided in HIBP_SEARCH_DOMAIN must have been verified in the domains dashboard
   environment = [
    "HIBP_TOKEN=<YOUR TOKEN>",
    "HIBP_SEARCH_DOMAIN=<domain to search>"
   ]

  commands = [
    "/usr/local/src/telegraf_plugins/hibp-domain-search.py",
  ]
  
  interval = 90m  
  timeout = "60s"
  name_suffix = ""
  data_format = "influx"
```

Note: the default measurement name is `hibp_domain_search`, you can override that by setting env var `INFLUXBD_MEASUREMENT` in your telegraf configuration.

**You should not set the interval too low: the API is rate limited and results do not change very often.**


### Monitoring Multiple Domains

If you wish to monitor multiple domains, you'll need to define multiple `inputs.exec` sections.

If you do this, to prevent excess load on the API (and avoid being rate limited), it'd be prudent to use `collection_offset` to ensure that the checks don't all run at the same time.


### Output

Output metrics are grouped in one of three ways.

#### Grouped by email

These metrics carry tag `by` with the value `email`. They describe how many times a given email address has been detected in breaches.

```text
hibp_domain_search,by=email,email=alice@example.com,search_domain=example.com,mbox=alice count=1i
hibp_domain_search,by=email,email=bob@example.com,search_domain=example.com,mbox=bob count=3i
hibp_domain_search,by=email,email=mallory@example.com,search_domain=example.com,mbox=mallory count=2i
```

#### Grouped by pwned service

These metrics carry tag `by` with the value `pwned_site`. They describe how many mailboxes have been impacted by that service

```text
hibp_domain_search,by=pwned_site,service=123RF,search_domain=example.com count=2i,emails="alice@example.com,bob@example.com"
hibp_domain_search,by=pwned_site,service=Apollo,search_domain=example.com count=1i,emails="mallory@example.com"
```

### Grouped by search domain 

This metric provides an overall count of affected mailboxes for the searched domain. It carries tag `by` with value `search_domain`

```text
hibp_domain_search,by=search_domain,search_domain=example.invalid count=0i
```

---

### Copyright

Copyright (c) 2024 [Ben Tasker](https://www.bentasker.co.uk)

Released under [MIT License](https://www.bentasker.co.uk/pages/licenses/mit-license.html)
