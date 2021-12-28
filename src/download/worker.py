from threading import Thread
from download import objects, dl_utils
import hashlib
import zlib
import time
import logging
import os


class DLWorker():
    def __init__(self, data, path, api_handler, gameId):
        self.data = data
        self.path = path
        self.api_handler = api_handler
        self.gameId = gameId
        self.completed = False
        self.logger = logging.getLogger("DOWNLOAD_WORKER")
        self.cancelled = False
        
    def do_stuff(self, is_dependency=False):
        item_path = os.path.join(self.path, self.data.path)
        if os.path.exists(item_path) and self.data.sha256 and (dl_utils.calculatesha256_sum(item_path) != self.data.sha256):
            self.completed = True
            return
        if os.path.exists(item_path):
            os.remove(item_path)
        for index in range(len(self.data.chunks)):
            chunk = self.data.chunks[index]
            if self.cancelled:
                break
            compressed_md5 = chunk['compressedMd5']
            md5 = chunk['md5']
            if is_dependency:
                url = dl_utils.get_dependency_link(self.api_handler, dl_utils.galaxy_path(compressed_md5))
            else:
                url = dl_utils.get_secure_link(self.api_handler, dl_utils.galaxy_path(compressed_md5), self.gameId)
            download_path = os.path.join(
                self.path, self.data.path+f'.tmp{index}')
            dl_utils.prepare_location(
                dl_utils.parent_dir(download_path), self.logger)
            self.get_file(url, download_path, compressed_md5, md5, index)
        for index in range(len(self.data.chunks)):
            path = os.path.join(self.path, self.data.path)
            self.decompress_file(path+f'.tmp{index}', path)
        self.completed = True

    def decompress_file(self, compressed, decompressed):
        if os.path.exists(compressed):
            file = open(compressed, 'rb')
            dc = zlib.decompress(file.read(), 15)
            f = open(decompressed, 'ab')
            f.write(dc)
            f.close()
            file.close()
            os.remove(compressed)

    def get_file(self, url, path, compressed_sum='', decompressed_sum='', index=0):
        isExisting = os.path.exists(path)
        if isExisting:
            os.remove(path)
        with open(path, 'ab') as f:
            response = self.api_handler.session.get(
                url, stream=True, allow_redirects=True)
            total = response.headers.get('Content-Length')
            if total is None:
                f.write(response.content)
            else:
                total = int(total)
                for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                    f.write(data)
            f.close()
            isExisting = os.path.exists(path)
            if isExisting and (hashlib.md5(open(path, 'rb').read()).hexdigest() != compressed_sum):
                self.logger.warning(
                    f'Checksums dismatch for compressed chunk of {path}')
                if isExisting:
                    os.remove(path)
                self.get_file(url, path, compressed_sum,
                              decompressed_sum, index)