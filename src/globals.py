from micropython import const

CK_BOOT_NR = 'boot_nr'
CK_DAY_CHANGED = 'day_changed'
CK_DAY_NR = 'day_nr'
CK_LAST_BOOT_DATE = 'last_boot_day'
CK_FIRST_BOOT_DATE = 'first_boot_day'
CK_RTC_SET = 'rtc_set'
CK_UPDATE_AVAILABLE = 'update'

CK_OP_FREQ = 10
# CK_BOOT_UPDATE_NR = 1         #check for update after every X boots
CK_SLEEP_FOR = 15*60             #sleep for X seconds
# CK_CHANGE_DAY_AFTER_BOOTS = int(24 * 60 / CK_SLEEP_FOR) + 1
# CK_SLEEP_AFTER = 180             #go to sleep (no matter what) after X seconds
# CK_SEND_DATA_EVERY = 7          #send data after every X boots
# CK_SEND_LOG_EVERY = 12          #send log after every X boots
# CK_UPDATE_WAITING_FOR = 300     #X seconds for the update to happen
# CK_MOVE_LOGS_WAITING_FOR = 120  #X seconds to move logs from /flash to /sd
CK_WDT_TIMEOUT = 180
CK_WDT_DOWNLOAD_TIMEOUT = 120
CK_UPDATES_ENABLED = False
CK_FREE_SPACE_THRESHOLD = 2.0

CK_MQTT_SERVER = 'lmi034-1.cs.uit.no'
CK_MQTT_PORT = 31417
CK_MQTT_USER = 'ou'
CK_MQTT_PASSWD = 'e90be0bf9fce33ab9c6f6b99d551e603f82897bd'
CK_MQTT_TEMP = 'temperature'
CK_MQTT_SQ = 'signal_quality'
CK_MQTT_SYS_VER = 'system_version'

CK_SD_MOUNT_POINT = '/sd'
CK_FLASH_LOG_DIR = '/flash/logs'
CK_SD_LOG_DIR = '{}/logs'.format(CK_SD_MOUNT_POINT)
CK_FLASH_DATA_DIR = '/flash/data'
CK_SD_DATA_DIR = '{}/data'.format(CK_SD_MOUNT_POINT)
CK_LOG_FILES_PATTERN = ['{}.txt', '{}._aggr.txt']
CK_DATA_FILES_PATTERN = ['temp-{}.txt']

CK_TCP_SERVER = 'lmi034-1.cs.uit.no'
# CK_TCP_SERVER = '10.128.0.182'
CK_TCP_PORT = 31416
CK_TCP_BUFF_SIZE = 1024

# CK_UDP_SERVER = 'lmi034-1.cs.uit.no'
CK_UDP_SERVER = '129.242.17.213'
CK_UDP_PORT = 31415
CK_NBIOT_PART_SIZE = 240

RADIO_LTE = const(1)
RADIO_NBT = const(2)
RADIO_WLAN = const(3)
ALLOWED_COM_RADIO = [RADIO_NBT]

# Code for aggregated logs
DEINIT = 'DEINIT'
BOOT = 'BOOT'
F_SENDING = 'F_SENDING'
TRACEBACK = 'TRACEBACK'
WATCHDOG = 'WDT'
LTE_OBJ_INIT = 'LTE_OBJ_INIT'
LTE_RESET = 'LTE_RESET'
LTE_NET_INIT = 'LTE_NET_INIT'
LTE_PROV = 'LTE_PROV'
LTE_ATTACH = 'LTE_ATTACH'
LTE_CONNECT = 'LTE_CONNECT'
LTE_DISC = 'LTE_DISC'
LTE_DETACH = 'LTE_DETACH'
LTE_DEINIT = 'LTE_DEINIT'
LTE_SQ = 'LTE_SQ'
LTE_SQ_T = 'LTE_SQ_T'
NBIOT_RESET = 'NB_RESET'
NBIOT_RADIO_ON = 'NB_ON'
NBIOT_APN = 'NB_APN'
NBIOT_OP = 'NB_PROV'
NBIOT_ATT = 'NB_ATTACH'
NBIOT_PDP = 'NB_PDP'
NBIOT_SOCK = 'NB_SOCK'
NBIOT_DISC = 'NB_DISC'
NBIOT_DEINIT = 'NB_DEINIT'
NBIOT_SQ = 'NB_SQ'
NBIOT_SQ_T = 'NB_SQ_T'

CK_SYSTEM_VERSION = '0.97'