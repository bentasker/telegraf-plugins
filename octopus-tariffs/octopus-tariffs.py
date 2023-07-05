#!/usr/bin/env python3

from datetime import datetime as dt
from datetime import timedelta as tdel
import os
import requests
import base64


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
    result = session.get(f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{meter['tariff-code']}/standard-unit-rates?period_from={from_str}")

    for pricepoint in result.json()['results']:
        meter['pricing'].append(pricepoint)
            
    return meter
    
def generateLP(addresses):
    ''' Take the built dict and generate multiple lines of LP
    '''
    
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
                priceToLP(price, meter['tariff-code'])
                        
def priceToLP(price, tariff_code):
    ''' Take a pricing dict and generate LP
    '''
    {'value_exc_vat': 29.2574, 'value_inc_vat': 30.72027, 'valid_from': '2023-06-30T23:00:00Z', 'valid_to': None, 'payment_method': 'DIRECT_DEBIT'}
    

    tags = [
        "octopus_pricing", # the measurement name
        f"payment_method={price['payment_method']}",
        f"tariff_code={tariff_code}"
        ]
    
    fields = [
            f"cost_exc_vat={price['value_exc_vat']}",
            f"cost_inc_vat={price['value_inc_vat']}",
            f"valid_from=\"{price['valid_from']}\"",
            f"valid_to=\"{price['valid_to']}\""
        ]
    
    lp = " ".join([','.join(tags), ','.join(fields)])
    print(lp)
    
    # We now need to generate a line for every 30 minutes between valid_from and valid_to
    # if valid_to is "None" we should use now()
    

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
                
        prop_info['meters'].append(meter_info)
    addresses.append(prop_info)
    
    print(addresses)
    generateLP(addresses)


if __name__ == "__main__":
    api_key = os.getenv("OCTOPUS_KEY", False)
    mpan = os.getenv("OCTOPUS_ACCOUNT", False)
    main(api_key, mpan)