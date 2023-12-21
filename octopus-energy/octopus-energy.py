#!/usr/bin/env python3
#
# Telegraf exec plugin to poll the Octopus API and retrieve
# pricing and consumption information
#
# Copyright (c) 2023, B Tasker
# Released under BSD 3-Clause License
#

'''
Copyright (c) 2023, B Tasker

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of
conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials
provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used
to endorse or promote products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from datetime import datetime as dt
from datetime import timedelta as tdel
from dateutil import parser
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
    tariff_direction = "UNKNOWN"
    
    # Currently the tariff direction is only on the products listing, so we need to retrieve that and iterate
    # through the products looking for the product code.
    result = session.get(f"https://api.octopus.energy/v1/products/?period_from={from_str}")    
    for product in result.json()['results']:
        if product['code'] == product_code:
            tariff_direction = product['direction']
            break
    
    # We can now use this to retrieve pricing
    #
    # TODO: we should check if the meter records the tariff type as STANDARD 
    # if not, we should be looking at day-unit/night-unit
    result = session.get(f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{meter['tariff-code']}/standard-unit-rates?period_from={from_str}")

    for pricepoint in result.json()['results']:
        pricepoint['type'] = "usage-charge"
        pricepoint['tariff_direction'] = tariff_direction
        meter['pricing'].append(pricepoint)
            
    # We also need to grab the daily standing charges
    result = session.get(f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{meter['tariff-code']}/standing-charges?period_from={from_str}")

    for pricepoint in result.json()['results']:
        pricepoint['type'] = "standing-charge"
        pricepoint['tariff_direction'] = tariff_direction
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
                    "meter_serial" : "",
                    "region_code" : meter['region']
                }
            
            if "serial" in meter:
                base_tagset['meter_serial'] = meter['serial']
                
            # Iterate through prices
            for price in meter['pricing']:
                # Don't output pricing information that flows in the wrong direction
                #
                # See comment on utilities/telegraf-plugins#17 for why this is needed
                if ((meter['is_export'] and price['tariff_direction'] == "EXPORT") or
                    (not meter['is_export'] and price['tariff_direction'] == "IMPORT")):
                        lp_buffer = lp_buffer + priceToLP(price, meter['tariff-code'])
                
            # and through consumption
            if "consumption" in meter:
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
        f"tariff_code={meter['tariff-code']}",
        f"is_export={str(meter['is_export'])}"
        ]
    
    fields = [
            f"consumption={consumed['consumption']}",            
        ]
    
    # Calculate the timestamp
    # timezones can fluctuate
    try:
        ts = int(parser.parse(consumed['interval_end']).strftime('%s'))
    except:
        ts = int(parser.parse(consumed['interval_end']).strftime('%s'))
    
    return " ".join([','.join(tags), ','.join(fields), str(ts * 1000000000)])
    
    
    
def priceToLP(price, tariff_code):
    ''' Take a pricing dict and generate LP
    '''
    

    tags = [
        "octopus_pricing", # the measurement name
        f"payment_method={price['payment_method']}",
        f"tariff_code={tariff_code}",
        f"charge_type={price['type']}",
        f"tariff_direction={price['tariff_direction']}"
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
        valid_to = int(parser.parse(price['valid_to']).strftime('%s'))
                               
    valid_from = int(parser.parse(price['valid_from']).strftime('%s'))
    
    # Iterate through
    lp_buffer = []
    while valid_from < valid_to:
        lp_buffer.append(f"{lp} {(valid_from + 1800)  * 1000000000}")
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
                "is_export" : meter_point['is_export'],
                "pricing" : []
            }
            for meter in meter_point['meters']:
                meter_info['serial'] = meter['serial_number']
                
            for agreement in meter_point['agreements']:
                ''' agreements lists all agreements against this meter
                
                    We need to iterate through them and take only the most
                    recent, so this is no longer valid (although the most
                    recent **should** be the last entry).
                
                meter_info = meter_info | {
                    
                    "tariff-code" : agreement['tariff_code'],
                    "from" : agreement['valid_from'],
                    "to" : agreement['valid_to']
                    }
                '''
                if "valid_to" in agreement and agreement["valid_to"]:
                    
                    try:
                        valid_to = int(parser.parse(agreement['valid_to']).strftime('%s'))
                    except:
                        valid_to = int(parser.parse(agreement['valid_to']).strftime('%s'))
                        
                    if int(dt.now().strftime('%s')) > valid_to:
                        continue
                    
                meter_info = meter_info | {
                    "tariff-code" : agreement['tariff_code'],
                    "from" : agreement['valid_from'],
                    "to" : agreement['valid_to']
                    }                
                
                
                
                # Get tariff info
                meter_info = getPricing(meter_info, session)

                # Get consumption
                if "serial" in meter_info:
                    meter_info['consumption'] = getConsumption(meter_info, session)
                
                # Create some LP for the meter itself
                lp = f'octopus_meter,mpan={meter_info["mpan"]},property={prop_info["id"]},account={prop_info["account_number"]},is_export={str(meter_info["is_export"])} start_date="{prop_info["start_date"]}" {int(dt.now().strftime("%s")) * 1000000000}'
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
