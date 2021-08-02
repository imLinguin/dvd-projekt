import requests
import logging
import sys
import os
import re
import zlib
import zipfile
import hashlib
import multiprocessing
import threading
import json as j
import locale
from utils import progressbar

_gog_content_system = 'https://content-system.gog.com/'
_gog_cdn = 'https://cdn.gog.com/'
_default_path = os.path.join(os.getenv('HOME'), 'dvdProjekt_Games')

platform = sys.platform


class DownloadManager():
    def __init__(self, config_manager, api_handler):
        self.config = config_manager
        self.api_handler = api_handler
        self.logger = logging.getLogger('DOWNLOAD')
        self.logger.setLevel(logging.INFO)
        self.lang = locale.getdefaultlocale()[0].replace('_', '-')
        self.cancelled = False
        self.depots = []
        self.workers = []

    def _get_library_os_name(self, x):
        if x == 'linux':
            return 'Linux'
        elif x == 'win32' or x == 'windows':
            return 'Windows'
        elif x == 'mac' or x == 'darwin':
            return 'Mac'

    def check_compatibility(self, game, target):
        self.logger.debug(f'Checking compatible platform {target}')
        key = self._get_library_os_name(target)
        if game['worksOn'][key]:
            return True
        else:
            return False

    def stop_workers(self):
        self.cancelled = True

    def init_download(self, args):
        if not self.api_handler.auth_status:
            self.logger.error('You have to be logged in')
            return
        game = self.api_handler.find_game(query=args.slug, key='slug')
        if not game:
            return
        if self.api_handler.is_expired():
            self.api_handler._refresh_token()
        self.logger.debug(f'Getting information for {game["id"]}')
        self.dl_id = game['id']
        data = self.api_handler.get_item_data(game['id'])
        # IDK if this is necessary
        if data and data['isPreOrder']:
            self.logger.warnig('You are trying to download preordered game, there is a chance there aren\'t any files to download')
        data['id'] = game['id']
        # Checking compatibility depending on user input or OS
        if not args.platform:
            if self.check_compatibility(game, 'linux'):
                self.download('Linux', data, args.path, args.lang)
            elif self.check_compatibility(game, 'windows'):
                self.logger.info('Using fallback platform: Windows')
                self.download('Windows', data, args.path, args.lang)
        else:
            if self.check_compatibility(game, args.platform):
                self.download(self._get_library_os_name(
                    args.platform), data, args.path, args.lang)
            else:
                self.logger.error('Specified platform isn\'t supported')
                return

    def download(self, system, game, path, lang):
        self.logger.info(f'Preparing to download {game["title"]}')
        if not path:
            path = _default_path
        if not lang:
            lang = 'en-US'
        self.lang = lang
        self.dl_path = path
        if system == "Linux":
            print("Linux downloads doesn't work for now")
            return
            # File which is being downloaded is a huge script which is an installer that also contains game data
            # TODO: Download script and handle it's execution maybe there is an optional argument for install path
            check = game['downloads'][0][1]['linux']
            if check:
                self.get_file(
                    f'https://embed.gog.com{check[0]["manualUrl"]}', path, False)
        elif system == "Windows":
            self.logger.debug('Getting Build data')
            builds = self.get_json(
                f'{_gog_content_system}products/{game["id"]}/os/windows/builds?generation=2')
            # Check if there is something to download :)
            if builds['count'] == 0:
                self.logger.error('Nothing to download, exiting')
                return
            meta_url = builds['items'][0]['link']

            self.logger.debug('Getting Metadata')
            meta = self.get_zlib_encoded(meta_url)
            # Metadata contains dependencies, might be useful when setting up WINE prefix
            self.dependencies = meta.get('dependencies')
            self.dl_path = os.path.join(self.dl_path, meta['installDirectory'])

            # Appends depots that are in specified language to array
            for i in range(len(meta['depots'])):
                depot = Depot(self.lang, meta['depots'][i])
                if not depot.check_language():
                    continue
                self.depots.append(depot)

            prepare_location(self.dl_path, self.logger)
            # TODO: Check available space on the disk
            self.total = 0
            # Execute download
            self.logger.info(f'Starting downloading in {self.dl_path}')

            # Collect all items to be downloaded
            download_items = []
            for depot in self.depots:
                manifest = self.get_zlib_encoded(
                    f'{_gog_cdn}content-system/v2/meta/{galaxy_path(depot.manifest)}')
                download_items += depot.get_depot_list(manifest)
            self.total += len(download_items)

            self.progress = progressbar.ProgressBar(0, self.total, 50)
            progress_worker = threading.Thread(
                target=self.progress.print_progressbar)
            # Split download_items equally to threads half of all cores in system for now
            # Tests required
            thread_count = int(max(1, multiprocessing.cpu_count()/2))
            splited_list = []
            step = round(self.total/thread_count)
            tmp = 0
            for thread in range(thread_count):
                start_index = thread*step
                end_index = thread*step+step
                end_index = min(end_index, len(download_items))
                splited_list.append(download_items[start_index:end_index])
                tmp += len(download_items[start_index:end_index])
                worker = threading.Thread(target=self.actual_downloader, args=[
                                          splited_list[thread], self.dl_path, thread])
                self.workers.append(worker)
                worker.start()
            progress_worker.start()
            # Wait for workers to complete
            for worker in self.workers:
                worker.join()
        self.logger.info('Download complete')

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

    def classify_cdns(self, array):
        best = None
        for item in array:
            if best is None:
                best = item
                continue
            # I'm not sure about that, research needed
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
                total = int(total)
                for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                    f.write(data)

        if compressed:
            decompress_path = path.replace('.tmp', '')
            tmp_file = open(path, 'rb')
            content = tmp_file.read()
            tmp_file.close()
            if hashlib.md5(content).hexdigest() != compressed_sum:
                self.logger.warning(f'Checksums dismatch for compressed chunk of {path}')
                os.remove(path)
                self.get_file(url, path, compressed_sum,
                              decompressed_sum, compressed)
                return
            self.decompress_file(path, decompress_path)
            tmp_file = open(decompress_path, 'rb')
            content = tmp_file.read()
            tmp_file.close()
            if hashlib.md5(content).hexdigest() != decompressed_sum:
                self.logger.warning(f'Checksums dismatch for decompressed {decompress_path}')
                os.remove(decompress_path)
                self.get_file(url, path, compressed_sum,
                              decompressed_sum, compressed)
                return

    def parent_dir(self, path: str):
        return path[0:path.rindex('/')]

    def decompress_file(self, compressed, decompressed):
        f = open(compressed, 'rb')
        dc = zlib.decompress(f.read(), 15)
        f.close()
        os.remove(compressed)
        f = open(decompressed, 'ab')
        f.write(dc)
        f.close()

    def actual_downloader(self, items, path, thread):
        while len(items) > 0 and not self.cancelled:
            item = items.pop(0)
            if type(item) == DepotDirectory:
                prepare_location(os.path.join(path, item.path), self.logger)
                continue
            for chunk in item.chunks:
                if self.cancelled:
                    break
                compressed_md5 = chunk['compressedMd5']
                md5 = chunk['md5']
                if os.path.isfile(os.path.join(path, item.path)):
                    if hashlib.md5(open(os.path.join(path, item.path), 'rb').read()).hexdigest() == md5:
                        continue
                url = self.get_secure_link(galaxy_path(compressed_md5))
                # return
                download_path = os.path.join(path, item.path+'.tmp')
                prepare_location(self.parent_dir(download_path), self.logger)
                self.get_file(url, download_path, compressed_md5, md5, True)

            self.progress.downloaded += 1


# ManifestV1 compatible if needed
def galaxy_path(manifest: str):
    galaxy_path = manifest
    if galaxy_path.find('/') == -1:
        galaxy_path = manifest[0:2]+'/'+manifest[2:4]+'/'+galaxy_path
    return galaxy_path


def prepare_location(path, logger):
    if not os.path.isdir(path):
        os.makedirs(path)
        if logger:
            logger.log(logging.DEBUG, f'Created directory in {path}')


class DepotFile():
    def __init__(self, item_data):
        self.path = item_data['path'].replace('\\', '/')
        self.chunks = item_data['chunks']
        self.sha254 = item_data.get('sha256')


# That exists in older depots, indicates directory to be created it, has only path in it
# Yes
class DepotDirectory():
    def __init__(self, item_data):
        self.path = item_data['path']


class Depot():
    def __init__(self, target_lang, depot_data):
        self.target_lang = target_lang
        self.languages = depot_data['languages']
        self.bitness = depot_data.get('osBitness')
        self.product_id = depot_data['productId']
        self.compressed_size = depot_data['compressedSize']
        self.size = depot_data['size']
        self.manifest = depot_data['manifest']

    def check_language(self):
        status = True
        for lang in self.languages:
            if lang == '*' or self.target_lang == lang or self.target_lang.split('-')[0] == lang:
                continue
            status = False
        return status

    def get_depot_list(self, manifest):
        download_list = list()
        for item in manifest['depot']['items']:
            obj = None
            if item['type'] == 'DepotFile':
                obj = DepotFile(item)
            else:
                obj = DepotDirectory(item)
            download_list.append(obj)
        return download_list
