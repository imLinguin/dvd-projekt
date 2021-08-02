import json
import os
from sys import platform
from api.wine import WineBinary


class ConfigManager():
    def __init__(self):
        self.path = '.'
        self._get_path()

    def _check_store(self, store):
        path = os.path.join(self.path, f'{store}.json') 
        if not os.path.isfile(path):
            f = open(path, 'w')
            f.write('{}')
            f.close()
            return False
        else:
            return True

    def save(self, store, data):
        with open(os.path.join(self.path, f'{store}.json'), 'w') as f:
            f.write(json.dumps(data))
            f.close()

    def read(self, store):
        try:
            if not self._check_store(store):
                return None
            with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
                data = json.loads(f.read() or '[]')
                f.close()
                return data
        except KeyError:
            return None

    def set_data(self, store, key, data):
        self._check_store(store)
        with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
            new_data = json.loads(f.read())
            f.close()
        with open(os.path.join(self.path, f'{store}.json'), 'w') as f:
            new_data[key] = data
            f.write(json.dumps(new_data))
            f.close()

    def get(self, store, key):
        try:
            if not self._check_store(store):
                return None
            with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
                content = f.read()
                if not content:
                    content = '{}'
                data = json.loads(content)
                if type(key) == list:
                    tab = []
                    for x in key:
                        tab.append(data[x])
                    return tab
                else:
                    return data[key]
                f.close()
        except KeyError:
            return None

    def logout_clean(self):
        with open(os.path.join(self.path, 'user.json'), 'w') as f:
            f.write('')
            f.close()
        with open(os.path.join(self.path, 'library.json'), 'w') as f:
            f.write('')
            f.close()

    def _get_path(self):
        if platform == 'linux':
            self.path = os.path.join(
                os.getenv("HOME"), '.config', 'dvdprojektTUX')

        # Make sure folder exists
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
