import requests
import logging
import sys
import os
import re
import zlib
import zipfile
import hashlib
import multiprocessing
import json as j

_gog_content_system = 'https://content-system.gog.com/'
_gog_cdn = 'https://cdn.gog.com/'
_default_path = os.path.join(os.getenv('HOME'), 'dvdProjekt Games')

platform = sys.platform


class DownloadManager():
    def __init__(self, config_manager, api_handler):
        self.config = config_manager
        self.api_handler = api_handler
        self.logger = logging.getLogger('DOWNLOAD')
        self.logger.setLevel(logging.INFO)
        self.workers = []

    def _get_library_os_name(self, x):
        if x == 'linux':
            return 'Linux'
        elif x == 'win32' or x == 'windows':
            return 'Windows'
        elif x == 'mac' or x == 'darwin':
            return 'Mac'

    def check_compatibility(self, game, target):
        self.logger.log(
            logging.DEBUG, f'Checking compatible platform {target}')
        key = self._get_library_os_name(target)
        if game['worksOn'][key]:
            return True
        else:
            return False

    def init_download(self, args):
        if not self.api_handler.auth_status:
            self.logger.log(logging.ERROR, 'You have to be logged in')
            return
        game = self.api_handler.find_game(query=args.slug, key='slug')
        if not game:
            return
        if self.api_handler.is_expired():
            self.api_handler._refresh_token()
        self.logger.log(logging.DEBUG, f'Getting information for {game["id"]}')
        self.dl_id = game['id']
        data = self.api_handler.get_item_data(game['id'])
        if data and data['isPreOrder']:
            self.logger.log(
                logging.WARNING, 'You are trying to download preordered game, there is a chance there aren\'t any files to download')
        data['id'] = game['id']
        if not args.platform:
            if self.check_compatibility(game, 'linux'):
                self.download('Linux', data, args.path)
            elif self.check_compatibility(game, 'windows'):
                self.logger.log(
                    logging.INFO, 'Using fallback platform: Windows')
                self.download('Windows', data, args.path)
        else:
            if self.check_compatibility(game, args.platform):
                self.download(self._get_library_os_name(
                    args.platform), data, args.path)
            else:
                self.logger.log(
                    logging.ERROR, 'Specified platform isn\'t supported')
                return

    def download(self, system, game, path):
        self.logger.log(logging.INFO, f'Preparing to download {game["title"]}')
        if not path:
            path = _default_path
        self.dl_path = path
        if system == "Linux":
            print("Linux downloads doesn't work for now")
            return
            check = game['downloads'][0][1]['linux']
            if check:
                self.get_file(
                    f'https://embed.gog.com{check[0]["manualUrl"]}', path, False)
        elif system == "Windows":
            self.logger.log(logging.DEBUG, 'Getting Build data')
            builds = self.get_json(
                f'{_gog_content_system}products/{game["id"]}/os/windows/builds?generation=2')
            if not builds:
                return
            # Check if there is something to download :)
            if builds['count'] == 0:
                self.logger.log(logging.ERROR, 'Nothing to download, exiting')
                return
            meta_url = builds['items'][0]['link']
            self.logger.log(logging.DEBUG, 'Getting Metadata')
            meta = self.get_zlib_encoded(meta_url)
            self.dl_path = os.path.join(self.dl_path, meta['installDirectory'])
            depot = meta['depots'][0]
            manifest_hash = depot['manifest']
            self.logger.log(logging.DEBUG, 'Getting Manifest')
            manifest = self.get_zlib_encoded(
                f'{_gog_cdn}content-system/v2/meta/{self.manifest_path(manifest_hash)}')

            self.create_depot_list(manifest)
            self.prepare_location(self.dl_path)
            self.actual_downloader()
        self.logger.log(logging.INFO, 'Download complete')

    def create_depot_list(self, manifest):
        self.dlitems = list()
        for item in manifest['depot']['items']:
            self.dlitems.append(DepotItem(item))

    def get_json(self, url):
        x = self.api_handler.session.get(url)
        if not x.ok:
            return
        return x.json()

    def get_zlib_encoded(self, url):
        x = self.api_handler.session.get(url)
        if not x.ok:
            return
        decompressed = j.loads(zlib.decompress(x.content, 15))
        return decompressed

    def get_secure_link(self, path):
        r = self.api_handler.session.get(
            f'https://content-system.gog.com/products/{self.dl_id}/secure_link?_version=2&generation=2&path={path}')
        if not r.ok:
            if self.api_handler.is_expired():
                self.api_handler._refresh_token()
                return self.get_secure_link(path)
        js = r.json()

        endpoint = self.classify_cdns(js['urls'])

        url_format = endpoint['url_format']
        parameters = endpoint['parameters']
        url = url_format
        for key in parameters.keys():
            url = url.replace('{'+key+'}', str(parameters[key]))
        if not url:
            print(endpoint)
        return url

    def manifest_path(self, manifest: str):
        galaxy_path = manifest
        if galaxy_path.find('/') == -1:
            galaxy_path = manifest[0:2]+'/'+manifest[2:4]+'/'+galaxy_path
        return galaxy_path

    def classify_cdns(self, array):
        best = None
        for item in array:
            if best is None:
                best = item
                continue
            if item['priority'] < best['priority']:
                best = item
        return best

    def get_file(self, url, path, compressed_sum='', decompressed_sum='', compressed=False):
        response = self.api_handler.session.get(
            url, stream=True, allow_redirects=True)
        total = response.headers.get('Content-Length')
        with open(path, 'ab') as f:
            if total is None:
                f.write(response.content)
            else:
                downloaded = 0
                total = int(total)
                for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                    downloaded += len(data)
                    f.write(data)
                    done = int(50*downloaded/total)
                    sys.stdout.write(
                        f'\r[{"█" * done}{"." * (50-done)}] {path.replace(".tmp", "")}')
                    sys.stdout.flush()
        sys.stdout.write('\n')
        if compressed:
            decompress_path = path.replace('.tmp', '')
            if hashlib.md5(open(path, 'rb').read()).hexdigest() != compressed_sum:
                self.logger.log(
                    logging.WARN, f'Checksums for compressed chunk of {decompress_path} not match, retrying')
                os.remove(path)
                self.get_file(url, path, compressed_sum, decompressed_sum, compressed)
                return
            self.decompress(path, path)
            if hashlib.md5(open(path, 'rb').read()).hexdigest() != decompressed_sum:
                self.logger.log(
                    logging.WARN, f'Checksums for decompressed {path} not match, retrying')
                os.remove(path)
                self.get_file(url, path, compressed_sum,
                              decompressed_sum, compressed)
                return
            os.rename(path, decompress_path)

    def parent_dir(self, path: str):
        return path[0:path.rindex('/')]

    def prepare_location(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
            self.logger.log(
                logging.INFO, f'Created directory in {path}')

    def decompress(self, compressed, decompressed):
        f = open(compressed, 'rb')
        dc = zlib.decompress(f.read(), 15)
        f.close()
        os.remove(compressed)
        f = open(decompressed, 'ab')
        f.write(dc)
        f.close()

    def actual_downloader(self):
        while len(self.dlitems) > 0:
            item = self.dlitems.pop(0)
            for chunk in item.chunks:
                compressed_md5 = chunk['compressedMd5']
                md5 = chunk['md5']
                url = self.get_secure_link(self.manifest_path(compressed_md5))
                download_path = os.path.join(self.dl_path, item.path+'.tmp')
                self.prepare_location(self.parent_dir(download_path))
                self.get_file(url, download_path, compressed_md5, md5, True)
        self.logger.log(logging.INFO, 'Everything downloaded, storing data in config')   

class DepotItem():
    def __init__(self, item_data):
        self.path = item_data['path'].replace('\\', '/')
        self.chunks = item_data['chunks']
        self.sha254 = item_data.get('sha256')
