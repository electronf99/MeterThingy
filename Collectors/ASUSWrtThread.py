import json
import threading
import time
from datetime import datetime

from Collectors.RouterInfo import RouterInfo

import pprint

class ASUSWrtThread(threading.Thread):

    def __init__(self):

        self.traffic={'speed': {'rx': 0, 'tx': 0},
                        'total': {'recv': 0, 'sent': 0},
                        'average': { 'rx': 0, 'tx': 0}
                        }
        self.average_speed={'speed': {'rx': 0, 'tx': 0},
                'total': {'recv': 0, 'sent': 0},
                'average': { 'rx': 0, 'tx': 0}
                }

        #self.router = RouterInfo("192.168.0.1", "admin", "electronf11")
        self.ri = RouterInfo("192.168.0.1", "admin", "electronf11")
        threading.Thread.__init__(self)

        
    def run(self):
        print("Started ASUSWrt Thread")

        start = datetime.now()
        interval = 0
        bytes_rx_last = 0
        bytes_tx_last = 0
                
        # Get Speed Loop

        while(1==1):
            try:
                self.ri = RouterInfo("192.168.0.1", "admin", "electronf11")           
                self.traffic = json.loads(self.ri.get_traffic())
                
                if bytes_rx_last == 0:
                    bytes_rx_last = self.traffic["total"]["recv"]
                    bytes_tx_last = self.traffic["total"]["sent"]

                # Get the difference in time between now and last loop

                diff_dt = datetime.now() - start
                interval = diff_dt.total_seconds()
                start = datetime.now()
                
                # Get total bytes dince last loop.

                bytes_rx_total = self.traffic["total"]["recv"]
                rx = bytes_rx_total - bytes_rx_last
                bytes_rx_last = bytes_rx_total

                bytes_tx_total = self.traffic["total"]["sent"]
                tx = bytes_tx_total - bytes_tx_last
                bytes_tx_last = bytes_tx_total

                # Grt speed over period 
                # I dont know why but the bytes for each period is half the actual value.

                average_rx = (rx / interval) * 2
                average_tx = (tx / interval) * 2

                
                # Stuff into dict

                self.average_speed["speed"]["rx"] = average_rx
                self.average_speed["speed"]["tx"] = average_tx
                
            except Exception as error:
                print("*****")
                print(error) 
            
            time.sleep(1)

    def get_latest(self):
        return self.average_speed  
