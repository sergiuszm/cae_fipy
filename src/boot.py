import pycom    
pycom.heartbeat_on_boot(False)
pycom.smart_config_on_boot(False)
pycom.wifi_on_boot(False)
import network
server = network.Server()
server.deinit() 

import src.logging as logging
from src.globals import CK_BOOT_NR, CK_DAY_CHANGED, CK_DAY_NR, CK_BOOT_UPDATE_NR, CK_MOVE_LOGS_WAITING_FOR, CK_SLEEP_FOR, CK_UPDATE_WAITING_FOR, CK_UPDATE_AVAILABLE, CK_SLEEP_AFTER, CK_WDT_TIMEOUT
from machine import WDT

_logger = logging.getLogger("boot")
wdt = WDT(timeout=CK_WDT_TIMEOUT * 1000)

def boot():
    import src.fileutil as fileutil
    if fileutil.isdir('/flash/logs') is False:
        from os import mkdir
        mkdir('/flash/logs')

    _logger.info('Booting')

    from src.pycom_util import mk_on_boot_fn
    boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
    boot_nr += 1
    mk_on_boot_fn(CK_BOOT_NR)(value=boot_nr)

    day_changed = mk_on_boot_fn(CK_DAY_CHANGED, default=0)()
    day_nr = mk_on_boot_fn(CK_DAY_NR, default=0)()

    _logger.info('Boot nr: %d. Day nr: %d', boot_nr, day_nr)
    
    from os import statvfs
    stat = statvfs('/flash')
    free_space = (stat[0] * stat[3]) / 1024.0 / 1024.0
    _logger.info('Free flash space: %f MB', free_space)

    # for testing
    if boot_nr >= CK_BOOT_UPDATE_NR:
        day_changed = True

    # Saving logs to SD card if day has changed
    if day_changed:
        from src.storage import uSD
        from src.setup import mosfet_sensors
        from machine import reset
        _logger.info('Day has changed (%d -> %d), mooving logs to SD', day_nr, day_nr + 1)

        mk_on_boot_fn(CK_DAY_CHANGED)(value=0)
        mosfet_sensors(True)
        sd = uSD()
        wdt.feed()
        sd.move_logs()
        sd.deinit()
        mosfet_sensors(False)
        day_nr += 1
        mk_on_boot_fn(CK_DAY_NR)(value=day_nr)
        _logger.info('Changing boot nr to: 0 - new day')
        mk_on_boot_fn(CK_BOOT_NR)(value=0)
        deinit_and_deepsleep(1)
    
    # It is time to check for updates so boot_nr is being reset to 1
    if boot_nr >= CK_BOOT_UPDATE_NR:
        _logger.info('Changing boot nr to: 1')
        boot_nr = 1
        mk_on_boot_fn(CK_BOOT_NR)(value=boot_nr)

    # boot_nr = 1: check for update and if there is one available prepare to download it next time
    # boot_nr = 2: if there is scheduled update then it will be downloaded and installed
    if boot_nr < 3:
        try:
            update_available = mk_on_boot_fn(CK_UPDATE_AVAILABLE, default=0)()
            if boot_nr == 1:
                _logger.info('Checking for update')
                connect_and_get_update()
            
            if boot_nr == 2 and update_available:
                connect_and_get_update()
        except Exception as e:
            _logger.error('Update failed. Reason %s', e)

        deinit_and_deepsleep(1)

    # Normal stage of execution
    _logger.info('Normal stage of execution')
    from src.main import main
    main()

def connect_and_get_update():
    from src.comm import WLAN, LTE
    radios = [LTE(), WLAN()]
    connected = False
    selected_radio = None
    for radio in radios:
        try:
            radio.connect()
            connected = True
            selected_radio = radio
            break
        except Exception as e:
            _logger.error('Connecting failed. Cause: %s. Repeating with next radio...', e)
            radio.deinit()
            continue

    if connected:
        from src.ota_updater import OTAUpdater
        token='ceab660119b1b41a87055d1b2eb9715c946a00b3'
        updater = OTAUpdater('https://github.com/sergiuszm/cae_fipy', headers={'Authorization': 'token {}'.format(token)})
        updater.download_and_install_update_if_available()
        selected_radio.deinit()

def deinit_and_deepsleep(sleep_for=CK_SLEEP_FOR):
    from src.setup import mosfet_sensors, disable_radios
    from time import sleep
    from machine import deepsleep

    mosfet_sensors(False)
    disable_radios()
    _logger.info('Going into deepsleep for %d s ...', sleep_for)
    deepsleep(sleep_for * 1000)

try:
    from machine import reset_cause, WDT_RESET, reset
    if WDT_RESET == reset_cause():
        _logger.info('WDT reset happened!')
        deinit_and_deepsleep()
    boot()
    deinit_and_deepsleep()
except Exception as e:
    _logger.traceback(e)
    deinit_and_deepsleep()
