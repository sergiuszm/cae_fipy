# main.py -- put your code here!

import time
from machine import UART, Pin
from src.commands import Commands
from src.thread import Thread
import pycom
from src.nbiotpy import NbIoT


def detect_beacon():
    from network import Bluetooth
    import ubinascii

    bt = Bluetooth()
    bt.start_scan(-1)

    def get_adv():
        while True:
            adv = bt.get_adv()

            if adv:
                
                name = bt.resolve_adv_data(adv.data, Bluetooth.ADV_NAME_CMPL)
                # if name not in ['Holy', 'Fipy']:
                if name is None:
                    continue
                
                # pycom.rgbled(0xff00)
                # time.sleep(1)
                # pycom.rgbled(0x0000)
                # try to get the complete name
                print('########################################')
                print("NAME: [{}] {}".format(adv.rssi, name))
                print("MAC: {}".format(ubinascii.hexlify(adv.mac).decode('utf-8')))
                mfg_data = bt.resolve_adv_data(adv.data, Bluetooth.ADV_MANUFACTURER_DATA)

                if mfg_data:
                    mfg_data = ubinascii.hexlify(mfg_data).decode('utf-8')
                    # try to get the manufacturer data (Apple's iBeacon data is sent here)
                    print("MFG DATA: %s" % (mfg_data))

                print("DATA: {}".format(ubinascii.hexlify(adv.data).decode('utf-8')))

                print('#############----------#################')

            time.sleep(1)

    Thread(get_adv).start()

# def update_lte():
#     from machine import SD
#     sd = SD()
#     os.mount(sd, '/sd')    # mount it
#     os.listdir('/sd')      # list its content

#     import sqnsupgrade
#     # sqnsupgrade.run('/sd/CATM1-41065/upgdiff_33080-to-41065.dup', '/sd/CATM1-41065/updater.elf')
#     sqnsupgrade.run('/sd/CATM1-41065/CATM1-41065.dup', '/sd/CATM1-41065/updater.elf')


# def get_lte_version():
#     import sqnsupgrade
#     print(sqnsupgrade.info())


def main():
    print('START!')
    from src.setup import mosfet_sensors, init_hw
    mosfet_sensors(True)
    init_hw()

    from src.sensors import read_temp
    read_temp()    

    from src.comm import LTE
    lte = LTE()
    lte.connect()

    from src.comm import NBT
    nbiot = NBT()
    nbiot.connect()
    nbiot.get_id()

    from src.storage import uSD
    sd = uSD()
    print(sd.list_files())
    sd.deinit()
    mosfet_sensors(False)

    # from comm import WLAN
    # wlan = WLAN()
    # wlan.connect()
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

