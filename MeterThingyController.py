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

def get_run_time():
    
    current_time = datetime.now()
    elapsed = current_time - start_time
    days = elapsed.days
    hours, remainder = divmod(elapsed.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration = f"{days} {hours:02}:{minutes:02}" 
    
    return duration

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
        "home" : "2C:CF:67:F3:AF:3D",
        "work" : "2C:CF:67:F3:AF:3D"
    }

    ble_address = ble_mac[location]
    characteristic_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
     
    # Startup thread to retrieve router stats from a COllector
    if location == "work":
        CollectorThread = LocalNetThread()
    else:
        CollectorThread = ASUSWrtThread()

    CollectorThread.start()



 
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

    # Create the bt transmitter object
    # Requedst a bt ack every ack_interval transmit loops
    transmitter =  Transmitter.Transmitter(ble_address, characteristic_uuid, ack_interval=20)

    # Start smoothing at 32768 (which is needle 0) Read later comments.
    m1_smoothed = 32768

    tx_time = 0

    last_fail_count = -1
    tx_count=0

    # Default Maximum Metric Value
    default_max_metric_value = 100

    while True:

        
        # An explanation of all the needle jiggery pokery
        #
        # The needle should be moved so that:
        #
        #   1. We dont hit the hard stop at the top because protect needle
        #   2. The moving iron part has inertia so stop it waving about
        #      by moving it's value up and down gradually
        #   3. Purely for looks, the needle should move down more slowly than up.
        #   4. The meter scale is non-linear in a non-linear fashion. Move it
        #      faster at the bottom in a kind of reverse exponential way.
        #   5. Sometimes it looks better to have a maximum metric value so that  
        #      the meter hangs around near the middle.
        #
        # IMPORTANT: The current Pico2 meter thingy is wired so that the output 
        #            driver sends 0v when the PWM duty cycle is set 32768. This is
        #            one way that the driver allows direction to be specified. The 
        #            moving iron meter always moves in the same direction and is
        #            generally used as an AC meter. (I should probably set direction
        #            with the driver dir pin)
        #            

        # Collect Data from collecter thread
        latest_data = CollectorThread.get_latest()
        metric_label = latest_data['v1']['label']
        metric_value = int(latest_data['v1']['value'])

        # Apply Collecter thread class specified maximum metric value
        max_metric_value = int(min(latest_data['v1']['max_value'], default_max_metric_value))
        metric_value = min(metric_value,max_metric_value)

        # Boost the needle at lower values
        metric_value_exp = reverse_exponential(metric_value, full_scale = max_metric_value, curve_factor = 4.0)

        # Needle 0 is duty 32768. The needle is 0 -> 100% at duty 32768 -> 65535
        # Calculate the duty as the ratio of (metric value / max value) * 32768
        needle_duty = (metric_value_exp/max_metric_value*32768)+32768
        
        # Final safewguard. Dont allow needle to swing all the way up to the stop
        max_needle_duty = 60000
        m1_duty = int(min(needle_duty, max_needle_duty))

        # Avoid waving due to iron inertia. and return to 0 slowly
        m1_smoothed = chaser(m1_duty, m1_smoothed, increment=2000, decrement=1000)
        data["meter"]["m1"]["v"] = m1_smoothed
        
        # How long since we started running
        duration = get_run_time()

        # Get failed packets in K
        failedK = "{:.1f}".format(transmitter.failed_packets/1000)

        load_average=os.getloadavg()[0]

        # Setup LCD Display Data
        data["LCD"]["0"] = f"{metric_label}{metric_value:02} PT{int(tx_time*1000)} L{load_average:.2f}           "[:16]
        data["LCD"]["1"] = f"{duration} F:{failedK}     "[:16]
      
        # Transmit data and return average packet time
        tx_time = await transmitter.transmit(data)
        tx_count += 1
        if last_fail_count != transmitter.failed_packets:
            now = datetime.now()
            print("--- failed ---")

            with open("/tmp/failed.out", "a") as file:
                file.write(f"{now.strftime('%Y-%m-%d %H:%M:%S')} UPTIME: {duration} PT: {tx_time:.3f} Dropped: {transmitter.failed_packets}/{transmitter.sent_packets} " +
                    f"{metric_label}: {metric_value:3d} LOADAVG: {load_average:.2f} {m1_smoothed}  [{'-' * int(metric_value / 4 ):<12}] [{'*' * int((m1_smoothed-32768) / 3000 ):<12}]\n")

        else:
            print(f"\r{now.strftime('%Y-%m-%d %H:%M:%S')} UPTIME: {duration} PT: {tx_time:.3f} Dropped: {transmitter.failed_packets}/{transmitter.sent_packets} " +
                    f"{metric_label}: {metric_value:3d} LOADAVG: {load_average:.2f} {m1_smoothed}  [{'-' * int(metric_value / 4 ):<12}] [{'*' * int((m1_smoothed-32768) / 3000 ):<12}]", end="\n")

        with open("/tmp/mt.out", "w") as file:
            file.write(f"\r{now.strftime('%Y-%m-%d %H:%M:%S')} UPTIME: {duration} PT: {tx_time:.3f} Dropped: {transmitter.failed_packets}/{transmitter.sent_packets} " +
                    f"{metric_label}: {metric_value:3d} LOADAVG: {load_average:.2f} {m1_smoothed}  [{'-' * int(metric_value / 4 ):<12}] [{'*' * int((m1_smoothed-32768) / 3000 ):<12}]")

        last_fail_count = transmitter.failed_packets

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run main with location context.")
    parser.add_argument("--location", choices=["home", "work"], default="home",
                        help="Specify the location: 'home' or 'work'")
    args = parser.parse_args()

    asyncio.run(main(args.location))
