# main.py -- put your code here!

import time
from machine import UART, Pin
from src.commands import Commands
from src.thread import Thread
import pycom
from src.nbiotpy import NbIoT
from src.setup import mosfet_sensors, init_hw
from src.ota_updater import OTAUpdater

def main():
    print('START!')
    
    mosfet_sensors(True)
    init_hw()

    # from src.sensors import read_temp
    # read_temp()    

    # from src.comm import LTE
    # lte = LTE()
    # lte.connect()

    # from src.comm import NBT
    # nbiot = NBT()
    # nbiot.connect()
    # nbiot.get_id()

    # from src.storage import uSD
    # sd = uSD()
    # print(sd.list_files())
    # sd.deinit()
    # mosfet_sensors(False)

    from src.comm import WLAN
    wlan = WLAN()
    wlan.connect()
    # token='ceab660119b1b41a87055d1b2eb9715c946a00b3'
    # updater = OTAUpdater('https://github.com/sergiuszm/cae_fipy', headers={'Authorization': 'token {}'.format(token)})
    # _, latest_version = updater.check_for_updates()
    # updater.check_for_update_to_install_during_next_reboot()
    # updater.download_update(latest_version)
    # Thread(wlan.connect).start()
    
    # from comm import LTE
    # lte = LTE()
    # Thread(lte.connect).start()


    # if not fileutil.isdir('/flash/data'):
    #     fileutil.mkdirs('/flash/data')

    # if not fileutil.isdir('/flash/log'):
    #     fileutil.mkdirs('/flash/log')


    # Thread(detect_beacon).start()
    # Thread(read_from_uart, commands).start()

    # Thread(cmd.disable_networks).start()
    # cmd.disable_networks()
    # Thread(test_nbiot).start()
    # Thread(sdcard_example).start()

