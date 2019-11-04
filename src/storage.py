from machine import SD
import os
import src.pycom_util as pycom_util
import src.sdcard as sdcard
import src.sdcard_wrapper as sdcard_wrapper
from machine import SPI
import _thread

class uSD:

    def __init__(self, cs_pin='P9', pins=('P10', 'P11', 'P14')):
        _spi = pycom_util.SpiWrapper()
        _spi.init(SPI.MASTER, pins=pins)
        self._sd = sdcard_wrapper.SdCardWrapper(_spi, pycom_util.PinWrapper(cs_pin))
        os.mount(self._sd, '/sd')
        self._lock = _thread.allocate_lock()

    def deinit(self):
        os.umount('/sd')
        self._sd = None

    def list_files(self):
        return os.listdir('/sd')
    
    def write(self, file_name, content):
        with self._lock:
            f = open('/sd/{}'.format(file_name), 'a')
            f.write(content)
            f.close()

    def sdcard_example():
        import _thread
        card = sdcard()
        # pycom.rgbled(0xff00)
        mount_sd_card(card)

        import os
        import time
        print(os.listdir('/sd'))
        
        a_lock = _thread.allocate_lock()

        def write_test(nr, lock):
            # lock.acquire()
            with lock:
                f = open('/sd/{}'.format('test{}.txt'.format(nr)), 'a')
                for x in range(0, 100):
                    f.write('{}\n'.format(x))
                f.close()
            # lock.release()
            print('Thread {} finished!'.format(nr))


        for x in range(0, 10):
            Thread(write_test, x, a_lock).start()

        # f = open('/sd/{}'.format('test1.txt'), 'a')
        # f.write('abcde')
        # f.close()

        print(os.listdir('/sd'))
