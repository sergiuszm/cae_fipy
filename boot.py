import pycom
from src.pycom_util import mk_on_boot_fn
from ota_updater import OTAUpdater
import src.logging as logging
from src.globals import *
from src.thread import Thread
from machine import deepsleep, reset
from time import sleep
from src.timeutil import TimedStep
from src.comm import WLAN, LTE
import gc

_logger = logging.getLogger("boot")

def boot():
    _logger.info('Booting')
    pycom.heartbeat(False)
    pycom.smart_config_on_boot(False)

    boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
    _logger.info('Boot nr: %d', boot_nr)
    # It is time to check for updates so boot_nr is being reset to 0
    if boot_nr >= CK_BOOT_UPDATE_NR:
        _logger.info('Changing boot nr to: 0')
        boot_nr = 0
        mk_on_boot_fn(CK_BOOT_NR)(value=boot_nr)

    boot_nr += 1
    mk_on_boot_fn(CK_BOOT_NR)(value=boot_nr)

    # boot_nr = 1: check for update and if there is one available prepare to download it next time
    # boot_nr = 2: if there is scheduled update then it will be downloaded and installed
    if boot_nr < 3:
        # we are giving it 120s to update
        Thread(sleep_for_seconds_after_seconds, after_seconds = 120, for_seconds = 1).start()
        try:
            connect_and_get_update()
        except Exception as e:
            _logger.error('Update failed. Reason %s', e)

        _logger.info('Disabling radios... Just in case.')
        reset()

    # Normal stage of execution
    Thread(sleep_for_seconds_after_seconds, for_seconds = 1, after_seconds = 60).start()
    print('Normal stage of execution')
    from src.main import main
    main()

def connect_and_get_update():
    radios = [WLAN.getInstance(), LTE.getInstance()]
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
        token='ceab660119b1b41a87055d1b2eb9715c946a00b3'
        updater = OTAUpdater('https://github.com/sergiuszm/cae_fipy', headers={'Authorization': 'token {}'.format(token)})
        updater.download_and_install_update_if_available()
        selected_radio.deinit()

def sleep_for_seconds_after_seconds(for_seconds=CK_SLEEP_FOR, after_seconds=CK_SLEEP_AFTER, threads=[]):
    num_threads_to_check = len(threads)
    _logger.info('Number of threads to go: %d', num_threads_to_check)
    num_threads_finished = 0
    seconds_left = after_seconds
    if num_threads_to_check == 0:
        sleep(after_seconds)
    else:
        for thread in threads:
            # print(thread.is_started())
            if not thread.is_started():
                _logger.info('Starting new thread')
                thread.start()
        
        with TimedStep('Threads total execution time', logger=_logger):
            while seconds_left > 0:
                for thread in threads:
                    # if not thread.is_started():
                    #     _logger.info('Starting new thread')
                    #     thread.start()

                    if thread.is_finished():
                        num_threads_finished += 1
                        _logger.info('Thread has finished. Threads to go: %d', (num_threads_to_check - num_threads_finished))

                if num_threads_finished == num_threads_to_check:
                    break

                seconds_left -= 1
                sleep(1)

    _logger.info('Going into deepsleep for %d s ...', for_seconds)
    deepsleep(for_seconds * 1000)

def disable_radios():
    radios = [WLAN.getInstance(), LTE.getInstance()]
    for radio in radios:
        radio.deinit()

boot()