#!/usr/bin/env python3

from datetime import datetime as dt
from datetime import timedelta as tdel
import os
import requests
import base64


def getConsumption(meter, session):
    ''' Call the API and fetch consumption information
    '''
    # Calculate the `from` date to apply (1 day ago)
    tday = dt.now()
    yday = tday - tdel(days=2)

    from_str = yday.strftime("%Y-%m-%d %H:%M:%SZ")
    
    result = session.get(f"https://api.octopus.energy/v1/electricity-meter-points/{meter['mpan']}/meters/{meter['serial']}/consumption?period_from={from_str}")    
    
    return result.json()['results']

def getPricing(meter, session):
    ''' Calculate the product code and fetch pricing info
    '''
    # We've got a tariff code (for example E-1R-VAR-22-11-01-A)
    # the product code is embedded into it - VAR-22-11-01
    # the A at the end of the example is the region code
    #
    # Split the tariff code up
    tariff_split = meter['tariff-code'].split("-")
    product_code = '-'.join(tariff_split[2:-1])
    meter['region'] = tariff_split[-1]
    
    # Calculate the `from` date to apply (1 day ago)
    tday = dt.now()
    yday = tday - tdel(days=1)

    from_str = yday.strftime("%Y-%m-%d %H:%M:%SZ")
    
    # We can now use this to retrieve pricing
    #
    # TODO: we should check if the meter records the tariff type as STANDARD 
    # if not, we should be looking at day-unit/night-unit
    result = session.get(f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{meter['tariff-code']}/standard-unit-rates?period_from={from_str}")

    for pricepoint in result.json()['results']:
        pricepoint['type'] = "usage-charge"
        meter['pricing'].append(pricepoint)
            
    # We also need to grab the daily standing charges
    result = session.get(f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{meter['tariff-code']}/standing-charges?period_from={from_str}")

    for pricepoint in result.json()['results']:
        pricepoint['type'] = "standing-charge"
        meter['pricing'].append(pricepoint)
        
    return meter
    
def generateLP(addresses):
    ''' Take the built dict and generate multiple lines of LP
    '''
    
    lp_buffer = []
    for address in addresses:
        base_tagset = {
            "address_id" : address['id'],
            "account_number" : address['account_number']           
            }
        
        # Iterate through any electricity meters
        for meter in address['meters']:
            tagset = base_tagset | {
                    "mpan" : meter['mpan'],
                    "meter_serial" : meter['serial'],
                    "region_code" : meter['region']
                }
            
            # Iterate through prices
            for price in meter['pricing']:
                lp_buffer = lp_buffer + priceToLP(price, meter['tariff-code'])
                
            # and through consumption
            for consumed in meter['consumption']:
                lp_buffer.append(consumedToLP(consumed, meter))
                
    return lp_buffer

def consumedToLP(consumed, meter):
    ''' Build LP indicating consumption 
    '''
    
    tags = [
        "octopus_consumption", # the measurement name
        f"mpan={meter['mpan']}",
        f"meter_serial={meter['serial']}",
        f"tariff_code={meter['tariff-code']}"
        ]
    
    fields = [
            f"consumption={consumed['consumption']}",            
        ]
    
    # Calculate the timestamp
    # timezones can fluctuate
    try:
        ts = int(dt.strptime(consumed['interval_end'], '%Y-%m-%dT%H:%M:%SZ').strftime('%s'))
    except:
        ts = int(dt.strptime(consumed['interval_end'], '%Y-%m-%dT%H:%M:%S+01:00').strftime('%s'))
    
    return " ".join([','.join(tags), ','.join(fields), str(ts * 1000000000)])
    
    
    
def priceToLP(price, tariff_code):
    ''' Take a pricing dict and generate LP
    '''
    {'value_exc_vat': 29.2574, 'value_inc_vat': 30.72027, 'valid_from': '2023-06-30T23:00:00Z', 'valid_to': None, 'payment_method': 'DIRECT_DEBIT'}
    

    tags = [
        "octopus_pricing", # the measurement name
        f"payment_method={price['payment_method']}",
        f"tariff_code={tariff_code}",
        f"charge_type={price['type']}"
        ]
    
    fields = [
            f"cost_exc_vat={price['value_exc_vat']}",
            f"cost_inc_vat={price['value_inc_vat']}",
            f"valid_from=\"{price['valid_from']}\"",
            f"valid_to=\"{price['valid_to']}\""
        ]
    
    lp = " ".join([','.join(tags), ','.join(fields)])
    
    # We now need to generate a line for every 30 minutes between valid_from and valid_to
    # if valid_to is "None" we should use now()
    #
    # Convert to epoch and then we can just iterate through in 30 min chunks
    if not price['valid_to']:
        valid_to = int(dt.now().strftime('%s'))
    else:
        valid_to = int(dt.strptime(price['valid_to'], '%Y-%m-%dT%H:%M:%SZ').strftime('%s'))
                               
    valid_from = int(dt.strptime(price['valid_from'], '%Y-%m-%dT%H:%M:%SZ').strftime('%s'))
    
    # Iterate through
    lp_buffer = []
    while valid_from < valid_to:
        lp_buffer.append(f"{lp} {valid_from * 1000000000}")
        valid_from = valid_from + 1800
        
    return lp_buffer


def main(api_key, octo_account):
    ''' Main entry point
    
    Fetch property details and identify meters
    '''
    if not api_key:
        return False
        
    # Set up a session allowing KA
    session = requests.session()
    auth_val = base64.b64encode(f"{api_key}:".encode('utf-8')).decode()
    headers = {
        "User-Agent" : "telegraf plugin (https://github.com/bentasker/telegraf-plugins/tree/master/octopus-tariffs)",
        "Authorization" : f"Basic {auth_val}"
        
        }
    # Make these the default
    session.headers = headers
    
    # Get Account info
    #
    # This gives us MPAN and tariff info
    result = session.get(f"https://api.octopus.energy/v1/accounts/{octo_account}")
    account = result.json()
        
    addresses = []
    lp_buffer = []
    # Iterate through addresses
    for prop in account['properties']:
        prop_info = {
            "id" : prop['id'],
            "meters" : [],
            "account_number" : octo_account,
            "start_date" : prop['moved_in_at']
        }
        # Iterate through meter points
        for meter_point in prop['electricity_meter_points']:
            meter_info = {
                "mpan" : meter_point['mpan'],
                "pricing" : []
            }
            for meter in meter_point['meters']:
                meter_info['serial'] = meter['serial_number']
                
            for agreement in meter_point['agreements']:
                meter_info = meter_info | {
                    
                    "tariff-code" : agreement['tariff_code'],
                    "from" : agreement['valid_from'],
                    "to" : agreement['valid_to']
                    }
                
                # Get tariff info
                meter_info = getPricing(meter_info, session)
                
                # Get consumption
                meter_info['consumption'] = getConsumption(meter_info, session)
                
                # Create some LP for the meter itself
                lp = f'octopus_meter,mpan={meter_info["mpan"]},property={prop_info["id"]},account={prop_info["account_number"]} start_date="{prop_info["start_date"]}" {int(dt.now().strftime("%s")) * 1000000000}'
                lp_buffer.append(lp)
                
        prop_info['meters'].append(meter_info)
    addresses.append(prop_info)
    
    # Turn it into LP
    lp_buffer = lp_buffer + generateLP(addresses)
    [print(x) for x in lp_buffer]


if __name__ == "__main__":
    api_key = os.getenv("OCTOPUS_KEY", False)
    mpan = os.getenv("OCTOPUS_ACCOUNT", False)
    main(api_key, mpan)