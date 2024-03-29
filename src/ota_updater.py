# Code from: https://github.com/rdehuyss/micropython-ota-updater
# @author rdehuyss

import usocket
import os
import gc
import machine
import src.logging as logging
from src.globals import CK_SYSTEM_VERSION, CK_UPDATE_AVAILABLE, CK_WDT_TIMEOUT
from src.pycom_util import mk_on_boot_fn
import src.fileutil as fileutil
from machine import WDT
from src.timeutil import TimedStep

_logger = logging.getLogger("ota_updater")

class OTAUpdater:

    def __init__(self, github_repo, module='', main_dir='src', headers={}):
        self.http_client = HttpClient(headers=headers)
        self.github_repo = github_repo.rstrip('/').replace('https://github.com', 'https://api.github.com/repos')
        self.main_dir = main_dir
        self.module = module.rstrip('/')
        self._wdt = WDT(timeout=CK_WDT_TIMEOUT * 1000)

    def download_and_install_update_if_available(self):
        def _download(latest_version):
            self.download_all_files(self.github_repo + '/contents/' + self.main_dir, latest_version)
            
        def _install(latest_version):
            self.rmtree(self.modulepath(self.main_dir))
            os.rename(self.modulepath('next/.version_on_reboot'), self.modulepath('next/.version'))
            os.rename(self.modulepath('next/.download_complete'), self.modulepath('next/.install_complete'))
            os.rename(self.modulepath('next'), self.modulepath(self.main_dir))
            _logger.info('Update installed (%s), will reboot now', latest_version)

        if 'next' in os.listdir(self.module):
            if '.version_on_reboot' in os.listdir(self.modulepath('next')):
                latest_version = self.get_version(self.modulepath('next'), '.version_on_reboot')
                _logger.info('New update found: %s', latest_version)
                self._wdt.feed()
                _download(latest_version)
                self._wdt.feed()
                if '.download_complete' in os.listdir(self.modulepath('next')):
                    _install(latest_version)
        else:
            self.check_for_update_to_install_during_next_reboot()

    def check_for_update_to_install_during_next_reboot(self):
        current_version, latest_version = self.check_for_updates()

        if latest_version > current_version:
            _logger.info('New version available, will download and install on next reboot')
            mk_on_boot_fn(CK_UPDATE_AVAILABLE)(value=1)
            if fileutil.isdir('/flash/next'):
                _logger.warning('Directory /flash/next should not exist but here we go... Removing.')
                self.rmtree(self.modulepath('next'))
            
            os.mkdir(self.modulepath('next'))
            with open(self.modulepath('next/.version_on_reboot'), 'w') as versionfile:
                versionfile.write(latest_version)
                versionfile.close()
        else:
            mk_on_boot_fn(CK_UPDATE_AVAILABLE)(value=0)

    def check_for_updates(self):
        current_version = self.get_version(self.modulepath(self.main_dir))
        latest_version = self.get_latest_version()

        _logger.info('Current version: %s', current_version)
        _logger.info('Latest version: %s', latest_version)

        return current_version, latest_version

    def rmtree(self, directory):
        for entry in os.ilistdir(directory):
            is_dir = entry[1] == 0x4000
            if is_dir:
                self.rmtree(directory + '/' + entry[0])

            else:
                os.remove(directory + '/' + entry[0])
        os.rmdir(directory)

    @staticmethod
    def get_version(directory, version_file_name='.version'):
        version = 0.0
        if version_file_name in os.listdir(directory):
            f = open(directory + '/' + version_file_name)
            version = f.read()
            f.close()
        
        if float(version) > float(CK_SYSTEM_VERSION):
            return version

        return CK_SYSTEM_VERSION

    def get_latest_version(self):
        with TimedStep('Checking latest version from repo', logger=_logger):
            latest_release = self.http_client.get(self.github_repo + '/releases/latest')
        
        try:
            version = latest_release.json()['tag_name']
            latest_release.close()        
        except KeyError as e:
            print(e)
            msg = 'Could not check for updates. Reason: %s' % e
            _logger.error(msg)
            latest_release.close()
            raise OTAUpdaterException(msg)
        
        return version

    def download_all_files(self, root_url, version):
        with TimedStep('Downloading update', logger=_logger):
            file_list = self.http_client.get(root_url + '?ref=refs/tags/' + version)
            for file in file_list.json():
                if file['type'] == 'file':
                    download_url = file['download_url']
                    download_path = self.modulepath('next/' + file['path'].replace(self.main_dir + '/', ''))
                    self.download_file(download_url.replace('refs/tags/', ''), download_path)
                elif file['type'] == 'dir':
                    path = self.modulepath('next/' + file['path'].replace(self.main_dir + '/', ''))
                    os.mkdir(path)
                    self.download_all_files(root_url + '/' + file['name'], version)

            file_list.close()
            with open(self.modulepath('next/.download_complete'), 'w') as d_file:
                d_file.write("1")
                d_file.close()

    def download_file(self, url, path):
        _logger.info('\tDownloading: %s', path)
        with open(path, 'w') as outfile:
            try:
                response = self.http_client.get(url)
                outfile.write(response.text)
            finally:
                response.close()
                outfile.close()
                gc.collect()

    def modulepath(self, path):
        return self.module + '/' + path if self.module else path


class OTAUpdaterException(Exception):
    pass


class Response:

    def __init__(self, f):
        self.raw = f
        self.encoding = 'utf-8'
        self._cached = None

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)

    def json(self):
        import ujson
        return ujson.loads(self.content)


class HttpClient:

    def __init__(self, headers={}):
        self._headers = headers

    def request(self, method, url, data=None, json=None, headers={}, stream=None):
        def _write_headers(sock, _headers):
            for k in _headers:
                sock.write(b'{}: {}\r\n'.format(k, _headers[k]))

        try:
            proto, dummy, host, path = url.split('/', 3)
        except ValueError:
            proto, dummy, host = url.split('/', 2)
            path = ''
        if proto == 'http:':
            port = 80
        elif proto == 'https:':
            import ussl
            port = 443
        else:
            raise ValueError('Unsupported protocol: ' + proto)

        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)

        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        ai = ai[0]

        s = usocket.socket(ai[0], ai[1], ai[2])
        try:
            s.connect(ai[-1])
            if proto == 'https:':
                s = ussl.wrap_socket(s, server_hostname=host)
            s.write(b'%s /%s HTTP/1.0\r\n' % (method, path))
            if not 'Host' in headers:
                s.write(b'Host: %s\r\n' % host)
            # Iterate over keys to avoid tuple alloc
            _write_headers(s, self._headers)
            _write_headers(s, headers)

            # add user agent
            s.write('User-Agent')
            s.write(b': ')
            s.write('MicroPython OTAUpdater')
            s.write(b'\r\n')
            if json is not None:
                assert data is None
                import ujson
                data = ujson.dumps(json)
                s.write(b'Content-Type: application/json\r\n')
            if data:
                s.write(b'Content-Length: %d\r\n' % len(data))
            s.write(b'\r\n')
            if data:
                s.write(data)

            l = s.readline()
            # print(l)
            l = l.split(None, 2)
            status = int(l[1])
            reason = ''
            if len(l) > 2:
                reason = l[2].rstrip()
            while True:
                l = s.readline()
                if not l or l == b'\r\n':
                    break
                # print(l)
                if l.startswith(b'Transfer-Encoding:'):
                    if b'chunked' in l:
                        raise ValueError('Unsupported ' + l)
                elif l.startswith(b'Location:') and not 200 <= status <= 299:
                    raise NotImplementedError('Redirects not yet supported')
        except OSError:
            s.close()
            raise

        resp = Response(s)
        resp.status_code = status
        resp.reason = reason
        return resp

    def head(self, url, **kw):
        return self.request('HEAD', url, **kw)

    def get(self, url, **kw):
        return self.request('GET', url, **kw)

    def post(self, url, **kw):
        return self.request('POST', url, **kw)

    def put(self, url, **kw):
        return self.request('PUT', url, **kw)

    def patch(self, url, **kw):
        return self.request('PATCH', url, **kw)

    def delete(self, url, **kw):
        return self.request('DELETE', url, **kw)
