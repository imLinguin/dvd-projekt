class DepotFile():
    def __init__(self, item_data):
        self.path = item_data['path'].replace('\\', '/')
        self.chunks = item_data['chunks']
        self.sha256 = item_data.get('sha256')


# That exists in older depots, indicates directory to be created, it has only path in it
# Yes that's the thing
class DepotDirectory():
    def __init__(self, item_data):
        self.path = item_data['path']


class Depot():
    def __init__(self, target_lang, depot_data):
        self.target_lang = target_lang
        self.languages = depot_data['languages']
        self.bitness = depot_data.get('osBitness')
        self.product_id = depot_data['productId']
        self.compressed_size = depot_data['compressedSize']
        self.size = depot_data['size']
        self.manifest = depot_data['manifest']

    def check_language(self):
        status = True
        for lang in self.languages:
            if lang == '*' or self.target_lang == lang or self.target_lang.split('-')[0] == lang:
                continue
            status = False
        return status

    def get_depot_list(self, manifest):
        download_list = list()
        for item in manifest['depot']['items']:
            obj = None
            if item['type'] == 'DepotFile':
                obj = DepotFile(item)
            else:
                obj = DepotDirectory(item)
            download_list.append(obj)
        return download_list
