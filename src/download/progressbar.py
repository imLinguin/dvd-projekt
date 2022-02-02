import sys
import time
import threading
from download import dl_utils


class ProgressBar(threading.Thread):
    def __init__(self, max_val, readable_download_size, length):
        self.downloaded = 0
        self.total = max_val
        self.readable_total = readable_download_size
        self.length = length
        self.completed = False
        self.downloaded_since_update = 0
        self.last_update = time.time()
        super().__init__(target=self.print_progressbar)

    def print_progressbar(self):
        done = 0

        while True:
            done = round(self.length*(self.downloaded/self.total))
            readable_downloaded = dl_utils.get_readable_size(self.downloaded)
            readable_speed = dl_utils.get_readable_size(self.downloaded_since_update / (time.time() - self.last_update))
            sys.stdout.write(
                f'\r[{"█" * int(done)}{"." * (self.length-int(done))}] Downloaded: {round(readable_downloaded[0],2)}{readable_downloaded[1]} of {self.readable_total} Speed: {readable_speed[0]:0.2f} {readable_speed[1]}/s ')
            sys.stdout.flush()
            self.downloaded_since_update = 0
            self.last_update = time.time()
            time.sleep(0.5)
            if(self.completed):
                break
        sys.stdout.write('\r')
        sys.stdout.flush()

    def update_downloaded_size(self, addition):
        self.downloaded+=addition
        self.downloaded_since_update+=addition