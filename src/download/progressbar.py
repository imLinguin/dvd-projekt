import sys
import time
import threading


class ProgressBar(threading.Thread):
    def __init__(self, current, max_val, length):
        self.downloaded = current
        self.active_threads = 0
        self.total = max_val
        self.length = length
        self.completed = False
        super().__init__(target=self.print_progressbar)

    def print_progressbar(self):
        done = 0
        # Substract main and progress threads
        while True:
            if(self.completed):
                break
            done = int(self.length*self.downloaded/self.total)
            sys.stdout.write(
                f'\r[{"█" * done}{"." * (self.length-done)}] Downloaded: {self.downloaded} of {self.total}, Download Threads: {self.active_threads}')
            sys.stdout.flush()

            time.sleep(1)
        sys.stdout.write('')
        sys.stdout.flush()
