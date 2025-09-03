#!/usr/bin/python3

import asyncio
from time import sleep
import time
from datetime import timedelta
import math

from MeterThingy import Transmitter
from Collectors.ASUSWrtThread import ASUSWrtThread

program_start_time = time.time()

def chaser(desired, current_value, increment):

    #print(f"[Worker] Counter: {desired}")

    if current_value != desired:
        if current_value - desired < increment:
            current_value += increment
        if current_value < desired:
            current_value += 1

        elif current_value - desired > increment:
            current_value -= increment
            if current_value > desired:
                current_value -= 1
    
    return current_value

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

async def main():

    ble_address = "2C:CF:67:E4:D5:10"
    characteristic_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    #data = b"Hello BLE"

    ASUS = ASUSWrtThread()
    ASUS.start()
    
    max_rx_speed = 50
    m1_smoothed = 32768

    transmit_duration_ms = 0
    transmit_total = 0
    transmit_avg = 0
    transmit_loops = 0

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
            },
    }

    transmitter =  Transmitter.Transmitter(ble_address, characteristic_uuid)

    while True:
        router_info = ASUS.get_latest()
        router_rx_speed = int(router_info['speed']['rx']) #* 3
        if router_rx_speed > 50:
            router_rx_speed=50
        
        router_rx_exp = reverse_exponential(router_rx_speed, full_scale = 50.0, curve_factor = 4.0)
            
        m1_duty = int(min((router_rx_exp/max_rx_speed*32768)+32768, 65535))
        
        m1_smoothed = chaser(m1_duty, m1_smoothed, 2000)
        

        data["meter"]["m1"]["v"] = m1_smoothed

        total_seconds = int(time.time() - program_start_time)
        duration = str(timedelta(seconds=total_seconds))
        duration.replace("days,", "" )
        duration.replace("day,", "" )
        
        data["LCD"]["0"] = f"fp: {str(transmitter.failed_packets)} A{transmit_avg:.3f}"
        data["LCD"]["1"] = f"{duration} RX{router_rx_speed}   "

        start_transmit = time.time()
        transmit_loops += 1
        
        await transmitter.transmit(data)

        transmit_duration_ms = float(timedelta(seconds = time.time() - start_transmit) / timedelta(milliseconds=1))/1000
        transmit_total += transmit_duration_ms
        transmit_avg = transmit_total / transmit_loops

        print(f"BLE Last: {transmit_duration_ms:.3f} " +
               f"BLE Average: {transmit_avg:.3f} Dropped: {transmitter.failed_packets} " +
                f"RX: {router_rx_speed:3d} RX_EXP: {router_rx_exp} UPTIME: {duration} {'-' * int(router_rx_speed / 3 )}")



if __name__ == "__main__":
    asyncio.run(main())