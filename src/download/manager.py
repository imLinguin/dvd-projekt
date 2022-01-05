import os
import locale
import constants
import logging
import json
import requests
import threading
from time import sleep
from multiprocessing import cpu_count
from download import dl_utils, objects, movie, file_dl
from download.worker import DLWorker
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
            if args.platform != "linux":
                self.platform = args.platform
            else:
                print("Linux downloads are not supported at the moment")
                return False

        is_compatible = self.check_compatibility()
        self.logger.info(f'Game is {"compatible" if is_compatible else "incompatible"}')
        if not is_compatible:
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
        if not args.path:
            self.dl_path = constants.DEFAULT_GAMES_PATH
            self.dl_path = os.path.join(
                self.dl_path, install_directory)
        else:
            self.logger.info(f'Custom path provided {args.path}')
            self.dl_path = args.path
        # TODO: Handle Dependencies
        self.dependencies = self.handle_dependencies()

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

        for depot in self.meta['depots']:
            if str(depot['productId']) == str(self.dl_target['id']):
                # TODO: Respect user language
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
        self.logger.info("Currently V1 Depots are not supported yet.")
        exit(0)
        collected_depots = []
        download_files = []
        dependencies = []

        for depot in self.meta['product']['depots']:
            if not 'redist' in depot:
                depot_object = objects.DepotV1(self.lang, depot)
                if depot_object.check_language():
                    collected_depots.append(depot_object)
            else:
                dependency_object = objects.DependencyV1(depot)
                dependencies.append(dependency_object)

        self.logger.debug(f"Collected {len(collected_depots)} depots, proceeding to download, Dependencies Depots: {len(dependencies)}")
        self.logger.info("Getting data manifests of the depots")
        
        for depot in collected_depots:
            # url = f'{constants.GOG_CDN}/content-system/v2/meta/{depot.manifest}'
            url = f'{constants.GOG_CDN}/content-system/v1/manifests/{self.game["id"]}/windows/{self.builds["items"][0]["legacy_build_id"]}/{depot.manifest}'
            manifest = dl_utils.get_json(self.api_handler, url)
            download_files += manifest['depot']['files']

        dl_utils.prepare_location(self.dl_path, self.logger)
        self.logger.info("Downloading main.bin file")
        if file_dl.get_file(f'{constants.GOG_CDN}/content-system/v1/depots/{self.game["id"]}/main.bin', self.dl_path, self.api_handler, self.logger, False):
            self.unpack_v1(download_files)
        else:
            print("")
            self.logger.error("Error downloading a file")
        return False

    def handle_dependencies(self):
        dependencies_json = self.api_handler.get_dependenices_list()
        dependencies_array = []
        if self.depot_version == 2 and not 'dependencies' in self.meta:
            return []
        # TODO: Do more research on games with V1 depots
        iterator = self.meta['dependencies'] if self.depot_version == 2 else self.meta['product']['gameIDs'][0]['dependencies']

        for dependency in dependencies_json['depots']:
            for game_dep in iterator:
                if dependency['dependencyId'] == game_dep:
                    dependencies_array.append(dependency)
        return dependencies_array

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
        if self.platform == "linux":
            self.logger.error("Linux installers are not supported yet")
            return False
        return self.dl_target['worksOn'][tester[self.platform]]

    def unpack_v1(self, download_files):
        self.logger.info("Unpacking main.bin (fs intense thing)")

    def calculate_size(self, files, dependencies):
        self.logger.info("Calculating download size")
        download_size = 0
        disk_size = 0
        for file in files:
            if type(file) == objects.DepotFile:
                for chunk in file.chunks:
                    download_size+=int(chunk['compressedSize'])
                    disk_size+=int(chunk['size'])

        for dependency in dependencies:
            for chunk in dependency.chunks:
                download_size+=int(chunk['compressedSize'])
                disk_size+=int(chunk['size'])

        return (download_size, disk_size)