from bleak import BleakClient, BleakError, BleakScanner
import msgpack
from MeterThingy.ble20Packets import ble20Packets
import time
from time import sleep


class Transmitter:
    def __init__(self, address: str, char_uuid: str):
        self.address = address
        self.char_uuid = char_uuid
        self.client = BleakClient(address)
        self.packer = ble20Packets(message_id=1, max_payload=17)
        self.failed_packets = 0

    async def connect(self):
        sleep(1)
        self.client
        try:
            await self.client.connect()
            print(f"Connected to {self.address}")
        except BleakError as e:
            print(f"Connection failed: {e}")
            await BleakScanner.discover(timeout=5.0)
            raise

    async def disconnect(self):
        if self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected")

    async def send_data(self, data: bytes, ack):
        if not self.client.is_connected:
            print("Not Connected")
            await self.connect()
        try:
            await self.client.write_gatt_char(self.char_uuid, data, ack)
            time.sleep(0.05)
            #print(f"Sent: {data}")
        except BleakError as e:
            print(f"Write failed: {e}")
            raise

    async def transmit(self, data: dict, wait):
        
        # Packet list handler

        mpack = msgpack.packb(data)
        packets = self.packer.build_packets(mpack)
        duration = 0
        try:
            start_time = time.perf_counter()
            count = 1
            for packet in packets:
                count += 1
                if wait is True and count == len(packets):
                    print("Waiting")
                    ack = True
                else:
                    ack = False
                await self.send_data(packet, ack)
            end_time = time.perf_counter()
            duration = (end_time - start_time) / float(len(packets))

        except Exception as e:
            print(f"Error: {e}, disconnect")
            self.failed_packets += 1
            await self.disconnect()
        
        return duration

