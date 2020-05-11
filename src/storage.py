import os
from src.pycom_util import SpiWrapper, PinWrapper, mk_on_boot_fn
import src.sdcard as sdcard
import src.sdcard_wrapper as sdcard_wrapper
from machine import SPI
import _thread
from src.globals import CK_DAY_NR, CK_BOOT_NR, CK_FLASH_LOG_DIR, CK_SD_MOUNT_POINT
import src.fileutil as fileutil

class Flash:

    @staticmethod
    def remove_old_files(path, source_pattern):
        _logger = logging.getLogger("flash")
        current_day = mk_on_boot_fn(CK_DAY_NR, default=0)()
        with TimedStep('Removing old files', logger=_logger):
            exclude = []
            for source in source_pattern:
                exclude.append(source.format(current_day))
                exclude.append(source.format(int(current_day) - 1))

            to_remove = []
            files = listdir(path)
            for f in files:
                if f in exclude:
                    continue

                file_path = '{}/{}'.format(path, f)
                to_remove.append(file_path)
                _logger.info('File {} has been selected for removal'.format(file_path))

            fileutil.remove_files(to_remove)

    @staticmethod
    def write(file_path, data):
        with open(file_path, 'a') as f:
            f.write('{}\n'.format(data))


class AggregatedMetric:

    @staticmethod
    def write(code, value):
        day_nr = mk_on_boot_fn(CK_DAY_NR, default=0)()
        boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
        path = '{}/{}_aggr.txt'.format(CK_FLASH_LOG_DIR, day_nr)
        with open(path, 'a') as f:
            f.write('{}|{}|{}\n'.format(boot_nr, code, value))


class uSD:

    def __init__(self, cs_pin='P9', pins=('P10', 'P11', 'P14')):
        self._spi = SpiWrapper()
        self._spi.init(SPI.MASTER, pins=pins)
        self._sd = sdcard_wrapper.SdCardWrapper(self._spi, PinWrapper(cs_pin))
        os.mount(self._sd, CK_SD_MOUNT_POINT)
        self._lock = _thread.allocate_lock()

    def deinit(self):
        os.umount(CK_SD_MOUNT_POINT)
        self._spi.deinit()
        self._sd = None

    def list_files(self):
        return os.listdir(CK_SD_MOUNT_POINT)
    
    def write(self, file_name, content):
        with self._lock:
            f = open('{}/{}'.format(CK_SD_MOUNT_POINT, file_name), 'a')
            f.write(content)
            f.close()

    def move_file(self, day_nr, f_name, source_path, dest_path):
        import src.logging as logging
        from src.timeutil import TimedStep

        _logger = logging.getLogger("storage", to_file=False)
        if fileutil.isdir(dest_path) is False:
            os.mkdir(dest_path)

        source = '{}/{}'.format(source_path, f_name)   
        if fileutil.isfile(source) is False:
            return

        destination = '{}/{}'.format(dest_path, f_name)

        with TimedStep('Moving file: {}'.format(f_name), logger=_logger):
            fileutil.copy_file(source, destination)
            os.remove(source)


