import os
import locale
import constants
import logging
import json
import requests
import threading
from time import sleep
from multiprocessing import cpu_count
from download import dl_utils, objects
from download.worker import DLWorker
from download.progressbar import ProgressBar
from sys import platform


class DownloadManager():
    def __init__(self, config_manager, api_handler, *args, **kwargs):
        self.config = config_manager
        self.api_handler = api_handler
        self.logger = logging.getLogger('DOWNLOAD_MANAGER')
        self.logger.setLevel(logging.INFO)
        self.lang = locale.getdefaultlocale()[0].replace('_', '-')
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def finish(self):
        installed_games = self.config.read('installed')
        if not installed_games:
            installed_games = []
        gameobj = {'slug': self.game['slug'],
                   'title': self.game['title'], 'path': self.dl_path, 'id': self.game['id']}
        added = False
        for igame in range(len(installed_games)):
            if installed_games[igame]['slug'] == gameobj['slug']:
                installed_games[igame] = gameobj
                break
        if not added:
            installed_games.append(gameobj)
        self.config.save('installed', installed_games)
        self.logger.info('Download complete')

    def download(self, args):

        if self.get_download_metadata(args):
            if self.perform_download():
                self.finish()

    # Get build and manifest data
    # This is windows like downloading
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
        self.logger.debug('Getting Build data')
        # Builds data
        self.builds = dl_utils.get_json(
            self.api_handler, f'{constants.GOG_CONTENT_SYSTEM}/products/{game["id"]}/os/windows/builds?generation=2')
        file = open("builds", 'w')
        file.write(json.dumps(self.builds))
        file.close()
        # Just in case
        if self.builds['count'] == 0:
            self.logger.error('Nothing to download, exiting')
            return False
        meta_url = self.builds['items'][0]['link']
        self.logger.debug('Getting Meta data')
        self.meta = dl_utils.get_zlib_encoded(self.api_handler, meta_url)
        file = open("meta", 'w')
        file.write(json.dumps(self.meta))
        file.close()
        self.game = game
        self.dependencies = self.meta.get('dependencies')
        self.dl_path = os.path.join(
            self.dl_path, self.meta['installDirectory'])
        return True

    def perform_download(self):
        # print(self.meta)
        self.logger.debug("Collecting base game depots")
        collected_depots = []
        for depot in self.meta['depots']:
            if str(depot['productId']) == str(self.dl_target['id']):
                # TODO: Respect user language
                collected_depots.append(objects.Depot('en-US', depot))
        self.logger.debug(
            f"Collected {len(collected_depots)} depots, proceeding to download")

        download_files = []
        for depot in collected_depots:
            manifest = dl_utils.get_zlib_encoded(
                self.api_handler, f'{constants.GOG_CDN}/content-system/v2/meta/{dl_utils.galaxy_path(depot.manifest)}')
            download_files += depot.get_depot_list(manifest)

        self.logger.debug(
            f"Downloading {len(download_files)} files, proceeding")

        self.active_threads = []
        allowed_threads = max(1, cpu_count())
        self.progress = ProgressBar(0, len(download_files), 50)
        self.progress.start()
        while True:
            for thread in range(len(self.active_threads)):
                if thread < len(self.active_threads):
                    self.active_threads[thread].cancelled = self.cancelled
                    if self.active_threads[thread].completed:
                        self.active_threads.pop(thread)
            self.progress.downloaded = self.progress.total - len(download_files)
            self.progress.active_threads = len(self.active_threads)
            if(len(self.active_threads) < allowed_threads) and not self.cancelled:
                if(len(download_files)<1):
                    break
                data = download_files.pop()
                thread = DLWorker(data, self.dl_path, self.api_handler, self.game['id'])
                # thread.logger.setLevel(self.logger.level)
                self.active_threads.append(thread)
                thread.start()
            else:
                sleep(0.1)
                if self.cancelled and len(self.active_threads) < 1:
                    break
        self.progress.downloaded = self.progress.total - len(download_files)
        self.progress.active_threads = len(self.active_threads)
        self.progress.completed = True
        return not self.cancelled
