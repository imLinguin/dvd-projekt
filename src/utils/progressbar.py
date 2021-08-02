import sys
import time
import threading

class ProgressBar():
    def __init__(self, current, max_val, length):
        self.downloaded = current
        self.total = max_val
        self.length = length
    def print_progressbar(self):
        done = 0
        # Substract main and progress threads
        while threading.active_count() - 2 > 0:
            done = int(self.length*self.downloaded/self.total)
            sys.stdout.write(f'\r[{"█" * done}{"." * (self.length-done)}] Downloaded: {self.downloaded} of {self.total}, Download Threads: {threading.active_count() - 2}')
            sys.stdout.flush()

            time.sleep(1)