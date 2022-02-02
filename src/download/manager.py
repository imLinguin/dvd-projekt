import os
import locale
import constants
import logging
import json
import requests
import threading
from time import sleep
from multiprocessing import cpu_count
from download import dl_utils, objects, movie, file_dl, linux
from download.worker import *
from download.progressbar import ProgressBar
from concurrent.futures import ThreadPoolExecutor
from sys import platform


class DownloadManager():
    def __init__(self, config_manager, api_handler, *args, **kwargs):
        self.config = config_manager
        self.api_handler = api_handler
        self.logger = logging.getLogger('DOWNLOAD_MANAGER')
        self.logger.setLevel(logging.INFO)
        self.lang = locale.getdefaultlocale()[0].replace('_', '-')
        self.cancelled = False

        self.platform = "windows" if platform == "win32" else "osx" if platform == "darwin" else "linux"


    def cancel(self):
        if self.thpool:
            self.logger.info("Shutting down thread pool")
            self.thpool.shutdown(wait=True, cancel_futures=True)
        self.cancelled = True
        exit(0)

    # Saves data about installed game in config
    def finish(self):
        installed_games = self.config.read('installed')
        if not installed_games:
            installed_games = []
        gameobj = {'slug': self.game['slug'],
                   'title': self.game['title'], 'path': self.dl_path, 'id': self.game['id'], 'build_id': self.builds['items'][0]['build_id'], 'platform': self.platform}
        added = False
        for igame in range(len(installed_games)):
            if installed_games[igame]['slug'] == gameobj['slug']:
                installed_games[igame] = gameobj
                added = True
                break
        if not added:
            installed_games.append(gameobj)
        self.config.save('installed', installed_games)
        self.logger.info('Download complete')

    def download(self, args):
        if self.get_download_metadata(args):
            if self.perform_download():
                self.finish()

    def get_download_metadata(self, args):
        # Fetches game data from cached library in .config/dvdProjektTUX/library.json
        self.logger.info(f'Searching for slug {args.slug}')
        game = self.api_handler.find_game(query=args.slug, key='slug')
        if not game:
            self.logger.error('Couldn\'t find what you are looking for')
            return
        self.logger.info(f'Found matching game {args.slug}')
        if not args.path:
            self.dl_path = constants.DEFAULT_GAMES_PATH
        else:
            self.logger.info(f'Custom path provided {args.path}')
            self.dl_path = args.path
        
        if not args.lang:
            config_lang = self.config.read_config_yaml().get("global").get("lang")
            if config_lang:
                self.lang = config_lang
        else:
            self.lang = args.lang

        # Getting more and newer data
        self.dl_target = self.api_handler.get_item_data(game['id'])
        self.dl_target['id'] = game['id']
        self.dl_target['slug'] = game['slug']
        self.dl_target['worksOn'] = game['worksOn']
        # If target is a movie handle it separately
        if game['isMovie']:
            try:
                movie.download_movie(game, self.api_handler)
            except KeyboardInterrupt:
                exit(0)
            return False
        # Handling platform Mac and Windows supported for now
        if args.platform:
            self.platform = args.platform

        is_compatible = self.check_compatibility()
        self.logger.info(f'Game is {"compatible" if is_compatible else "incompatible"}')
        if not is_compatible:
            return False
        if self.platform == "linux":
            linux.download(self.dl_target, self.api_handler, self.dl_path, self.config)
            return False
        self.logger.debug('Getting Build data')
        # Builds data
        self.builds = dl_utils.get_json(
            self.api_handler, f'{constants.GOG_CONTENT_SYSTEM}/products/{game["id"]}/os/{self.platform}/builds?generation=2')
        # Just in case
        if self.builds['count'] == 0:
            self.logger.error('Nothing to download, exiting')
            return False
        # Downloading most recent thing
        self.depot_version = self.builds['items'][0]['generation']
        if self.depot_version == 1 or self.depot_version == 2:
            self.logger.info(f"Depot version: {self.depot_version}")
        else:
            self.logger.error("Unsupported depot version please report this")
            return False
        meta_url = self.builds['items'][0]['link']
        self.logger.debug('Getting Meta data')
        self.meta = dl_utils.get_zlib_encoded(self.api_handler, meta_url)
        self.game = game
        install_directory = self.meta['installDirectory'] if self.depot_version == 2 else self.meta['product']['installDirectory']
        self.dl_path = os.path.join(
                self.dl_path, install_directory)
        # TODO: Handle Dependencies
        self.dependencies, self.redist_version = self.handle_dependencies()

        return True

    # V2 downloading
    def perform_download(self):
        # print(self.meta)
        if self.depot_version == 1:
            return self.perform_download_V1()
        self.logger.debug("Collecting base game depots")

        collected_depots = []
        download_files = []
        dependency_files = []

        owned_dlcs = []
        for dlc in self.meta['products']:
            if dlc['productId'] != self.meta['baseProductId']:
                if self.api_handler.does_user_own(dlc['productId']):
                    owned_dlcs.append(dlc['productId'])

        for depot in self.meta['depots']:
            if str(depot['productId']) == str(self.meta['baseProductId']) or depot['productId'] in owned_dlcs:
                newObject = objects.Depot(self.lang, depot)
                if newObject.check_language():
                    collected_depots.append(newObject)
        self.logger.debug(
            f"Collected {len(collected_depots)} depots, proceeding to download, Dependencies Depots: {len(self.dependencies)}")

        for depot in collected_depots:
            manifest = dl_utils.get_zlib_encoded(
                self.api_handler, f'{constants.GOG_CDN}/content-system/v2/meta/{dl_utils.galaxy_path(depot.manifest)}')
            download_files += self.get_depot_list(manifest)
        for depot in self.dependencies:
            manifest = dl_utils.get_zlib_encoded(
                self.api_handler, f'{constants.GOG_CDN}/content-system/v2/dependencies/meta/{dl_utils.galaxy_path(depot["manifest"])}')
            dependency_files += self.get_depot_list(manifest)

        self.logger.debug(
            f"Downloading {len(download_files)} game files, and {len(dependency_files)} dependency files proceeding")
        
        self.threads = []

        size_data = self.calculate_size(download_files, dependency_files)
        download_size = size_data[0]
        disk_size = size_data[1]

        readable_download_size = dl_utils.get_readable_size(download_size)
        readable_disk_size = dl_utils.get_readable_size(disk_size)
        self.logger.info(f"Download size: {round(readable_download_size[0], 2)}{readable_download_size[1]}")
        self.logger.info(f"Size on disk: {round(readable_disk_size[0], 2)}{readable_disk_size[1]}")

        if not dl_utils.check_free_space(disk_size, self.dl_path):
            self.logger.error("NOT ENOUGH SPACE ON DISK")
            exit(1)
        allowed_threads = max(1, cpu_count())
        self.logger.debug("Spawning progress bar process")
        self.progress = ProgressBar(download_size, f"{round(readable_download_size[0], 2)}{readable_download_size[1]}", 50)
        self.progress.start()

        self.thpool = ThreadPoolExecutor(max_workers=allowed_threads)
        
        # Main game files
        for file in download_files:
            thread = DLWorker(file, self.dl_path, self.api_handler, self.game['id'], self.progress.update_downloaded_size)
            self.threads.append(self.thpool.submit(thread.do_stuff))
        # Dependencies
        for file in dependency_files:
            thread = DLWorker(file, self.dl_path, self.api_handler, self.game['id'], self.progress.update_downloaded_size)
            self.threads.append(self.thpool.submit(thread.do_stuff, (True)))

        # Wait until everything finishes
        while True:
            is_done = False
            for thread in self.threads:
                is_done = thread.done()
                if is_done == False:
                    break
            if is_done:
                break
            sleep(0.5)
        # while True:
        #     if self.cancelled:
        #         for thread in range(len(self.active_threads)):
        #             if thread < len(self.active_threads):
        #                 self.active_threads[thread].cancelled = self.cancelled
        #     self.progress.downloaded = self.progress.total - len(download_files)
        #     self.progress.active_threads = len(self.active_threads)
        #     if(len(self.active_threads) < allowed_threads) and not self.cancelled:
        #         if(len(download_files)<1):
        #             break
        #         data = download_files.pop()
        #         thread = DLWorker(data, self.dl_path, self.api_handler, self.game['id'])
        #         # thread.logger.setLevel(self.logger.level)
        #         self.active_threads.append(thread)
        #         thread.start()
        #     else:
        #         sleep(0.1)
        #         if self.cancelled and len(self.active_threads) < 1:
        #             break
        # for th in self.active_threads:
        #     th.join()
        
        # self.progress.downloaded = self.progress.total - len(download_files)
        # self.progress.active_threads = len(self.active_threads)
        self.progress.completed = True
        return not self.cancelled

    def perform_download_V1(self):
        self.logger.debug("Redirecting download to V1 handler")
        collected_depots = []
        download_files = []
        collected_dependencies = []
        dependency_files = []
        
        for depot in self.meta['product']['depots']:
            if not 'redist' in depot:
                depot_object = objects.DepotV1(self.lang, depot)
                if depot_object.check_language():
                    collected_depots.append(depot_object)
            else:
                dependency_object = objects.DependencyV1(depot)
                collected_dependencies.append(dependency_object)

        self.logger.debug(f"Collected {len(collected_depots)} depots, proceeding to download, Dependencies Depots: {len(collected_dependencies)}")
        self.logger.info("Getting data manifests of the depots")
        
        for depot in collected_depots:
            # url = f'{constants.GOG_CDN}/content-system/v2/meta/{depot.manifest}'
            url = f'{constants.GOG_CDN}/content-system/v1/manifests/{self.game["id"]}/{self.platform}/{self.builds["items"][0]["legacy_build_id"]}/{depot.manifest}'
            manifest = dl_utils.get_json(self.api_handler, url)
            download_files += manifest['depot']['files']

        for depot in self.dependencies:
            url = f"{constants.GOG_CDN}/content-system/v1/redists/manifests/{self.redist_version}/{depot['manifest']}"
            repo = dl_utils.get_json(self.api_handler, url)
            for redist_file in range(len(repo['depot']['files'])):
                if depot['path'][0] == '/':
                    depot['path'] = depot['path'][1:]
                if repo['depot']['files'][redist_file]['path'][0] == '/':
                    repo['depot']['files'][redist_file]['path'] = repo['depot']['files'][redist_file]['path'][1:]
                
                repo['depot']['files'][redist_file]['path'] = os.path.join(depot['path'], repo['depot']['files'][redist_file]['path'])
                redistributable_id, file_name = repo['depot']['files'][redist_file]['url'].split('/')
                cdn_json = dl_utils.get_json(self.api_handler, f"{constants.GOG_CONTENT_SYSTEM}/open_link?_version=2&generation=1&path=redists/{redistributable_id}/{self.redist_version}")
                cdn = dl_utils.classify_cdns(cdn_json['urls'], 1)
                repo['depot']['files'][redist_file]['link'] = cdn['url']+'/main.bin'
            dependency_files.extend(repo['depot']['files'])


        dl_utils.prepare_location(self.dl_path, self.logger)
        link = dl_utils.get_secure_link(self.api_handler, f"/{self.platform}/{self.builds['items'][0]['legacy_build_id']}", self.game["id"], generation=1)
        
        size_data = self.calculate_size(download_files, [])
        download_size = size_data[0]
        disk_size = size_data[1]
        readable_download_size = dl_utils.get_readable_size(download_size)
        readable_disk_size = dl_utils.get_readable_size(disk_size)
        self.logger.info(f"Download size: {round(readable_download_size[0], 2)}{readable_download_size[1]}")
        self.logger.info(f"Size on disk: {round(readable_disk_size[0], 2)}{readable_disk_size[1]}")

        allowed_threads = max(1, cpu_count())
        self.thpool = ThreadPoolExecutor(max_workers=allowed_threads)

        self.logger.debug("Spawning progress bar process")
        self.progress = ProgressBar(download_size, f"{round(readable_download_size[0], 2)}{readable_download_size[1]}", 50)
        self.progress.start()
        self.threads = []
        for download_file in download_files:
            worker = DLWorkerV1(download_file, self.dl_path, link, self.api_handler, self.game['id'], self.progress.update_downloaded_size)
            thread = self.thpool.submit(worker.do_stuff, False)
            self.threads.append(thread)
        
        for download_file in dependency_files:
            worker = DLWorkerV1(download_file, self.dl_path, download_file['link'], self.api_handler, self.game['id'], self.progress.update_downloaded_size)
            thread = self.thpool.submit(worker.do_stuff, True)
            self.threads.append(thread)

        while True:
            is_done = False
            for thread in self.threads:
                is_done = thread.done()
                if is_done == False:
                    break
            if is_done:
                break
            sleep(0.1)

        self.progress.completed = True

        return True

    def handle_dependencies(self):
        dependencies_json, version = self.api_handler.get_dependenices_list(self.depot_version)
        dependencies_array = []
        if self.depot_version == 2 and not 'dependencies' in self.meta:
            return []
        old_iterator = []
        if self.depot_version == 1:
            old_iterator.extend(self.meta['product']['gameIDs'][0]['dependencies'])
            for depot in self.meta['product']['depots']:
                if 'redist' in depot:
                    old_iterator.append(depot)
        # TODO: Do more research on games with V1 depots
        iterator = self.meta['dependencies'] if self.depot_version == 2 else old_iterator

        for dependency in (dependencies_json['depots'] if self.depot_version == 2 else dependencies_json['product']['depots']):
            for game_dep in iterator:
                if self.depot_version == 2:
                    if dependency['dependencyId'] == game_dep:
                        dependencies_array.append(dependency)
                else:
                    if game_dep['redist'] in dependency['gameIDs']:
                        dependency['path'] = game_dep['targetDir']
                        dependency['redist'] = game_dep['redist']
                        dependencies_array.append(dependency)
        return dependencies_array, version
            


    def get_depot_list(self, manifest):
        download_list = list()
        for item in manifest['depot']['items']:
            obj = None
            if item['type'] == 'DepotFile':
                obj = objects.DepotFile(item)
            else:
                obj = objects.DepotDirectory(item)
            download_list.append(obj)
        return download_list

    def check_compatibility(self):
        self.logger.info(f"Checking compatibility of {self.dl_target['title']} with {self.platform}")
        tester = {
            'osx': 'Mac',
            'windows': 'Windows',
            'linux': 'Linux'
        }
        return self.dl_target['worksOn'][tester[self.platform]]

    def calculate_size(self, files, dependencies):
        self.logger.info("Calculating download size")
        download_size = 0
        disk_size = 0
        for file in files:
            if type(file) == objects.DepotFile and self.depot_version == 2:
                for chunk in file.chunks:
                    download_size+=int(chunk['compressedSize'])
                    disk_size+=int(chunk['size'])
            elif self.depot_version == 1:
                disk_size+=int(file['size'])
        for dependency in dependencies:
            if self.depot_version == 2:
                for chunk in dependency.chunks:
                    download_size+=int(chunk['compressedSize'])
                    disk_size+=int(chunk['size'])
            elif self.depot_version == 1:
                disk_size+=int(file['size'])
        if self.depot_version == 1:
            download_size = disk_size
        return (download_size, disk_size)