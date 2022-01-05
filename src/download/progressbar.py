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
        super().__init__(target=self.print_progressbar)

    def print_progressbar(self):
        done = 0

        while True:
            if(self.completed):
                break
            done = round(self.length*(self.downloaded/self.total))
            readable_downloaded = dl_utils.get_readable_size(self.downloaded)
            sys.stdout.write(
                f'\r[{"█" * int(done)}{"." * (self.length-int(done))}] Downloaded: {round(readable_downloaded[0],2)}{readable_downloaded[1]} of {self.readable_total}   ')
            sys.stdout.flush()

            time.sleep(1)
        sys.stdout.write('\r')
        sys.stdout.flush()

    def update_downloaded_size(self, addition):
        self.downloaded+=addition