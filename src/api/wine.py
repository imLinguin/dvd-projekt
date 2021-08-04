import logging
import os

_search_paths = ['$HOME/.steam/steam/steamapps/common/', '$HOME/.steam/root/compatibilitytools.d/']
_home_dir = os.getenv('HOME')
_config_store = 'wine_binaries'

class WineHandler():
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger('COMPATIBILITY')

    def find_binaries(self):
        found_versions = []
        for path in _search_paths:
            path = path.replace('$HOME', _home_dir)
            if os.path.isdir(path):
                potential_versions = os.listdir(path)
                for catalog in potential_versions:
                    binary_path = os.path.join(path, catalog, 'proton')
                    if not os.path.isdir(os.path.join(path, catalog)):
                        continue
                    if os.path.isfile(binary_path):
                        found_versions.append(WineBinary(binary_path, catalog))
        self.logger.info(f'Found {len(found_versions)} versions, {found_versions}')
        self.logger.debug('Saving to config')
        for version in range(len(found_versions)):
            found_versions[version] = {'binary_path': found_versions[version].binary_path, 'name': found_versions[version].name}
        self.config.set_data(_config_store, 'versions', found_versions)
        self.logger.debug('Saved')

    def list_binaries(self):
        binaries = self.config.read(_config_store)
        output = '** WINE BINARIES\n'
        for x in range(len(binaries['versions'])):
            output+=f'* [{"X" if binaries["default"] == x else " "}] {x+1}. {binaries["versions"][x]["name"]} {binaries["versions"][x]["binary_path"]}\n'
        if len(binaries['versions']) == 0:
            output += 'List is empty, add binary manualy or use scanning feature'
        print(output)
    
    def select_default(self, index):
        index = min(index, len(self.config.read(_config_store)['versions'])-1)
        self.config.set_data(_config_store, 'default', index)

class WineBinary():
    def __init__(self, binary, name):
        self.binary_path = binary
        self.name = name
    
    def __repr__(self):
        return f'Name: {self.name} Path: {self.binary_path}'
