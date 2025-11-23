#!/usr/bin/python3

import asyncio
import time
from datetime import datetime
import math
import os
import argparse

from MeterThingy import Transmitter
from Collectors.ASUSWrtThread import ASUSWrtThread
from Collectors.LocalNetThread import LocalNetThread

# Global variable to hold start_time
# It will keep updating regardless of what happens

program_start_time = time.time()
start_time = datetime.now()

# function that takes the desired value and increments it
# so that you can smooth out changes in value.
# Used by calling it with the last returned chaser value.
def chaser(desired, current_value, increment=100, decrement=100):

    if current_value != desired:
        
        # On the way up
        if current_value < desired:
            current_value += increment

        # On the way down
        if current_value > desired:
            current_value -= decrement
            if current_value < decrement:
                current_value = 0
        
    return current_value


# I want to be able to make the needle on meters move
# more aggresively at the bottom of the scale and
# slow down as it approaches full scale
# This is a reverse exponentiation 
# 
def reverse_exponential(input_value: float, full_scale: float = 15.0, curve_factor: float = 4.0) -> float:
    """
    Maps input_value (0.0 to 1.0) to a voltage with more movement at the bottom end.
    curve_factor > 1 makes the curve steeper at the bottom.
    """
    input_value = input_value/full_scale
    input_value = max(0.0, min(1.0, input_value))  # Clamp input
    shaped = 1 - math.exp(-curve_factor * input_value)
    normalized = shaped / (1 - math.exp(-curve_factor))
    return normalized * full_scale


# Main function. Async to handle threading bluetooth

async def main(location):

    # Using Mac. Should figure out how to find mac based on name.
    ble_mac = {
        "home" : "2C:CF:67:F3:AC:37",
        "work" : "2C:CF:67:F3:AC:37"
    }

    ble_address = ble_mac[location]
    characteristic_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
     
    # Startup thread to retrieve router stats from a COllector
    if location == "work":
        CollectorThread = LocalNetThread()
    else:
        CollectorThread = ASUSWrtThread()

    CollectorThread.start()

    max_rx_speed = 50
    max_load_avg_1 = 3
    m1_smoothed = 32768
    m2_smoothed = 1
 
    global program_start_time
    
    data = {
        "LCD": {
                "0": "This is a test",
                "1": "ddmmyy",
            },
        "meter": {
            "m1": {
                "v": 3,
                },
            "m2": {
                "v": 10000,
                },
            },
    }

    transmitter =  Transmitter.Transmitter(ble_address, characteristic_uuid)
    tx_time = 0
    slide_factor = 0
    last_fail_count = -1
    loop = 0
    while True:

        router_info = CollectorThread.get_latest()
        router_rx_speed = int(router_info['speed']['rx']) #* 3
        if router_rx_speed > 50:
            router_rx_speed=50
        
        
        load_average_1, load_5, load_15 = os.getloadavg()
        if load_average_1 > 5:
            load_average_1=5


        router_rx_exp = reverse_exponential(router_rx_speed, full_scale = 50.0, curve_factor = 4.0)

        m1_duty = int(min((router_rx_exp/max_rx_speed*32768)+32768, 65535))
        m1_smoothed = chaser(m1_duty, m1_smoothed, increment=3000, decrement=1000)
        data["meter"]["m1"]["v"] = m1_smoothed
        
        m2_duty = int(load_average_1/max_load_avg_1 * 65535)
        m2_smoothed = chaser(m2_duty, m2_smoothed, increment=1000, decrement=500)
        data["meter"]["m2"]["v"] = m2_smoothed + 1 #m2_duty


        current_time = datetime.now()
        elapsed = current_time - start_time

        # Break down the timedelta
        days = elapsed.days
        hours, remainder = divmod(elapsed.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)


        duration = f"{days} {hours:02}:{minutes:02}:{seconds:02}"
        
        slide_factor += 1

        data["LCD"]["0"] = f"R{router_rx_speed:02} PT{int(tx_time*1000)} L{load_average_1:.2f}           "[:16]
        data["LCD"]["1"] = f"{duration}          "[:16]
      
        # Transmit data and return averrage packet time

        # print(data)
        loop += 1
        if loop == 120:
            ack = True
            loop = 0
        else:
            ack = False
        
        tx_time = await transmitter.transmit(data, ack)

        if last_fail_count != transmitter.failed_packets:
            now = datetime.now()
            print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} UPTIME: {duration} PT: {tx_time:.3f} Dropped: {transmitter.failed_packets} " +
                    f"RX: {router_rx_speed:3d} RX_EXP: {router_rx_exp}  {'-' * int(router_rx_speed / 3 )}")
        else:
            #print(f"\r{' '*132}", end="")
            print(f"\r{now.strftime('%Y-%m-%d %H:%M:%S')} UPTIME: {duration} PT: {tx_time:.3f} Dropped: {transmitter.failed_packets} " +
                    f"RX: {router_rx_speed:3d} LOADAVG: {load_average_1:.2f} {m1_smoothed}  [{'-' * int(router_rx_speed / 4 ):<12}] [{'*' * int((m1_smoothed-32768) / 3000 ):<12}]", end="\n")


        last_fail_count = transmitter.failed_packets

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run main with location context.")
    parser.add_argument("--location", choices=["home", "work"], default="home",
                        help="Specify the location: 'home' or 'work'")
    args = parser.parse_args()

    asyncio.run(main(args.location))
