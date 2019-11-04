class Commands:
    # def __init__(self):
    #     print(dir(self))
    def help(self):
        to_remove = ['__qualname__', 'call_function', '__module__']
        tmp_fns = dir(self)
        fns = []
        for fn in tmp_fns:
            if fn in to_remove:
                continue

            fns.append(fn)

        return fns
            
    def list_files(self):
        from src.storage import SDCard
        sd = SDCard()
        print(sd.list_files())
        sd.deinit()
        del sd

    def write_to_file(self, file_name, content):
        print('Write to file')

    def disable_networks(self):
        from network import WLAN, Server, Bluetooth, LTE

        print('WLAN')
        wlan = WLAN()
        wlan.deinit()

        print('Bluetooth')
        bluetooth = Bluetooth()
        bluetooth.deinit()

        print('Server')
        server = Server()
        server.deinit()

        print('LTE')
        lte = LTE()
        lte.deinit()
        print('Networks disabled!')

    def call_function(self, name):
        fn = getattr(self, name, None)
        if fn is not None:
            return fn()