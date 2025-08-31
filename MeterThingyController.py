#!/usr/bin/python3
import asyncio
from time import sleep
from pprint import pprint

from bleak import BleakClient
import time
from datetime import timedelta
from BLEClasses.ble20Packets import ble20Packets
import msgpack


from Collectors.ASUSWrtThread import ASUSWrtThread


def chaser(desired, current_value, increment):

    print(f"[Worker] Counter: {desired}")

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




async def main(ASUS):

    ble_address = "2C:CF:67:E4:D5:10"
    characteristic_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

    # Packet list handler
    packer = ble20Packets(message_id=1, max_payload=17)
    
    transmission = {
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
    
    program_start_time = time.time()
 
    async with BleakClient(ble_address) as client:
        

        transmit_duration_ms = 0
        transmit_total = 0

        loops = 0
        transmit_avg = 0
        m1_smoothed = 32768
        max_rx_speed = 50

        while(1==1):
 
            router_info = ASUS.get_latest()
            router_rx_speed = int(router_info['speed']['rx']) * 3
            m1_duty = int(min((router_rx_speed/max_rx_speed*32768)+32768, 65535))

            m1_smoothed = chaser(m1_duty, m1_smoothed, 2000)
            print(router_rx_speed)


            print(f"{m1_duty} : {m1_smoothed}")
            
            transmission["meter"]["m1"]["val"] = str(m1_smoothed)
            
            transmission["LCD"]["0"] = f"{str(m1_duty)} A{transmit_avg:.3f}"
            total_seconds = int(time.time() - program_start_time)
            duration = str(timedelta(seconds=total_seconds))
            duration.replace("days", "" )
            transmission["LCD"]["1"] = f"{duration} RX{router_rx_speed}   "

            
            mpack = msgpack.packb(transmission)
            packets = packer.build_packets(mpack)

            start_transmit = time.time()
            loops += 1
            for packet in packets:
                #print(packet)
                try:
                    await client.write_gatt_char(characteristic_uuid, packet)
                except Exception as e:
                    print(f"Write failed: {e}")
                    await asyncio.sleep(2)  # Backoff before retry

            transmit_duration_ms = float(timedelta(seconds = time.time() - start_transmit) / timedelta(milliseconds=1))/1000
            transmit_total += transmit_duration_ms
            transmit_avg = transmit_total / loops

            sleep(0.01)


if __name__ == "__main__":
   
    ASUS = ASUSWrtThread()
    ASUS.start()

    while 1==1:
  
        sleep(1)
        try:
            asyncio.run(main(ASUS))
        except Exception as e:
            print(e)



