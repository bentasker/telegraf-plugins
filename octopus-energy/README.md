### Octopus Energy Telegraf Plugin

This is an exec based plugin for Telegraf designed to collect Electricity usage and tariff details from the [Octopus Energy API](https://developer.octopus.energy/docs/api/)

See [utilities/telegraf-plugins#14](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/14.html) for more information on the original intent of the plugin.


Note: Octopus fetch consumption from the meter once daily, so although this plugin can collect consumption it cannot provide a realtime view (you need something like the [Glow IHD](https://www.bentasker.co.uk/posts/blog/house-stuff/connecting-my-smart-meter-to-influxdb-using-telegraf-and-a-glow-display.html) or the [Octopus Home Mini](https://octopus.energy/blog/octopus-home-mini/) for that).


----

### Dependencies

* Python >= 3
* Python Requests Module

----

### Pre-Requisites

You will need 

* Your API key
* Your account number


----

### Telegraf Config

The API details can be passed via the `environment` configuration option

```ini
[[inputs.exec]]
    commands = [
        "/usr/local/src/telegraf_plugins/octopus-energy.py",
    ]
    timeout = "60s"
    interval = "1h"
    name_suffix = ""
    data_format = "influx"
    # Update the value of these
    environment = [
    "OCTOPUS_KEY=",
    "OCTOPUS_ACCOUNT="
    ]
```

The plugin doesn't need to be run too often - Octopus fetch consumption information from your meter once daily, so consumption stats are not generally available until the day after.

Tariff details (if you're on a tariff like Agile Octopus) are update more frequently though, so it's worth triggering the plugin once an hour to capture the latest pricing (as well as future pricing).

----

### Measurements and Fields

- `octopus_consumption`
    - Fields:
        - consumption (`kWh` consumed in period)
    - Tags:
        - meter_serial: serial number of the meter
        - mpan
        - tariff_code: Octopus's tariff code (allowing Joining to pricing info)
- `octopus_meter`
    - Fields:
        - start_date: when service started for this meter
    - Tags:
        - account: Octopus account number
        - mpan
        - property: Octopus property ID
- `octopus_pricing`
    - Fields:
        - cost_exc_vat: unit price excluding vat
        - cost_inc_vat: unit price including vat
        - valid_from: time price came into effect
        - valid_to: when price ends (or `None` if no current expiry)
    - Tags:
        - charge_type: Standing-charge or usage-charge
        - payment_method: whether it's the Direct Debit or Non Direct Debit price
        - tariff_code: The octopus tariff code
    
Notes:

- The `octopus_meter` measurement exists purely to make information on the meter available, it's most useful values are the tagset rather than the fields
- The timestamp used in `octopus_consumption` is the *end* of the indicated period, so if Octopus's API reports 1kWh used between 00:00 and 00:30, the timestamp on the point will be for 00:30
- For ease of joining, the timestamp used in `octopus_pricing` is the *end* of the indicated period, so if Octopus's API reports a price of 0.01 between 00:00 and 00:30, the timestamp on the point will be for 00:30
- For ease of joining, the plugin calculates `octopus_pricing` points every 30 minutes between `valid_from` and `valid_to`
- Export tariffs don't currently have any specific handling (that will be added later)
- Gas isn't currently handled

----

### Product Prefix Matching

When changing tariff, I had [some issues](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/17.html) with Octopus being slow to update the tariff-code reported for my meter. In Dec 2023 I experienced [a similar issue](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/18.html) as a result of them changing the format of the product code.

In theory, it's possible to derive a product code (needed to retrieve prices) from the tariff code listed for a meter:

- Tariff code `E-1R-VAR-22-11-01-A` maps to product code `VAR-22-11-01`

In Dec 23, however, Octopus updated the Agile code but not the original tariff code, with the result that `E-1R-AGILE-FLEX-22-11-25-A` didn't map to the new code (`AGILE-23-12-06`).

[utilities/telegraf-plugins#18](https://projects.bentasker.co.uk/gils_projects/issue/utilities/telegraf-plugins/18.html) introduced new controls to help handle occurrences like this:


```ini
[[inputs.exec]]
   interval = "15m"
   data_format = "influx"
   environment = [
    "OCTOPUS_KEY=<my_key>",
    "OCTOPUS_ACCOUNT=<my_account>",
    "IMPORT_PRODUCT_PREFIX=AGILE-23"
   ]
   commands = [
    "/usr/local/src/telegraf_plugins/octopus-energy.py"
   ]
```

Environment variables `IMPORT_PRODUCT_PREFIX` and `EXPORT_PRODUCT_PREFIX` can be used to provide the desired beginning of a product code. If an exact match is achieved first, that'll be used instead.


----

### License

Copyright 2023, B Tasker. Released under [BSD 3 Clause](https://www.bentasker.co.uk/pages/licenses/bsd-3-clause.html).
