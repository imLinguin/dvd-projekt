import json
import os


class ConfigManager():
    def __init__(self):
        self.path = '.'

    def save(self, store, data):
        with open(os.path.join(self.path, f'{store}.json'), 'w') as f:
            f.write(json.dumps(data))
            f.close()

    def read(self, store):
        with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
            data = json.loads(f.read())
            f.close()
            return data

    def set_data(self, store, key, data):
        with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
            new_data = json.loads(f.read())
        with open(os.path.join(self.path, f'{store}.json'), 'w') as f:
            new_data[key] = data
            f.write(json.dumps(new_data))
            f.close()

    def get(self, store, key):
        with open(os.path.join(self.path, f'{store}.json'), 'r') as f:
            content = f.read()
            data = json.loads(content)
            if type(key) == list:
                tab = []
                for x in key:
                    tab.append(data[x])
                return tab
            else:
                return data[key]
            f.close()

    def logout_clean(self):
        with open(os.path.join(self.path, f'user.json'), 'w') as f:
            f.write('')
            f.close()
