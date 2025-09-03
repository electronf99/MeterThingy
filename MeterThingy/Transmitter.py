from bleak import BleakClient, BleakError, BleakScanner
import msgpack
from MeterThingy.ble20Packets import ble20Packets
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

    async def send_data(self, data: bytes):
        if not self.client.is_connected:
            print("Not Connected")
            await self.connect()
        try:
            await self.client.write_gatt_char(self.char_uuid, data)
            #print(f"Sent: {data}")
        except BleakError as e:
            print(f"Write failed: {e}")
            raise

    async def transmit(self, data: dict):
        
        # Packet list handler

        mpack = msgpack.packb(data)
        packets = self.packer.build_packets(mpack)
    
        try:
            for packet in packets:
                await self.send_data(packet)
        except Exception as e:
            print(f"Error: {e}, disconnect")
            self.failed_packets += 1
            await self.disconnect()

