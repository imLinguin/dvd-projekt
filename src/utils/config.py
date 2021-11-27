import json
import yaml
import os
from sys import platform
from api.wine import WineBinary
import constants


class ConfigManager():
    def __init__(self):
        self.path = constants.CONFIG_PATH

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
        try:
            with open(os.path.join(self.path, 'user.json'), 'w') as f:
                f.write('')
                f.close()
            with open(os.path.join(self.path, 'library.json'), 'w') as f:
                f.write('')
                f.close()
        except:
            return False
        return True

    def read_config_yaml(self):
        yaml_path = os.path.join(self.path, 'config.yaml')
        if(os.path.exists(yaml_path)):
            config = yaml.load(open(yaml_path,'r'), yaml.Loader)
            return config
        else:
            file = open(yaml_path, 'w')
            yaml.dump({"global": {"gamemode":False}}, file)