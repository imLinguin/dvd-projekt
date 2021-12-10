import json
import zlib
import os
import constants
import hashlib

def get_json(api_handler, url):
    x = api_handler.session.get(url)
    if not x.ok:
        return
    return x.json()


def get_zlib_encoded(api_handler, url):
    x = api_handler.session.get(url)
    if not x.ok:
        return
    decompressed = json.loads(zlib.decompress(x.content, 15))
    return decompressed


def prepare_location(path, logger):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        if logger:
            logger.debug(f'Created directory {path}')

# V1 Compatible
def galaxy_path(manifest: str):
    galaxy_path = manifest
    if galaxy_path.find('/') == -1:
        galaxy_path = manifest[0:2]+'/'+manifest[2:4]+'/'+galaxy_path
    return galaxy_path


def get_secure_link(api_handler, path, gameId):
    r = api_handler.session.get(f'https://content-system.gog.com/products/{gameId}/secure_link?_version=2&generation=2&path={path}')
    if not r.ok:
       if api_handler.is_expired():
            api_handler._refresh_token()
            return get_secure_link(api_handler,path, gameId)
    js = r.json()

    endpoint = classify_cdns(js['urls'])
    url_format = endpoint['url_format']
    parameters = endpoint['parameters']
    url = url_format
    for key in parameters.keys():
        url = url.replace('{'+key+'}', str(parameters[key]))
    if not url:
        print(f"Error ocurred getting a secure link: {url}")
    return url

def parent_dir(path: str):
    return path[0:path.rindex('/')]


def classify_cdns(array):
    cdns = list()
    for item in array:
        score = 0
        endpoint_name = item['endpoint_name']
        # Some CDNS are failing to process a request propertly
        cdn = filterCdns(endpoint_name, constants.GALAXY_CDNS)
        if cdn:
            cdns.append(item)
    best = None
    for cdn in cdns:
        if not best:
            best = cdn
        else:
            if best['priority'] > cdn['priority']:
                best = cdn
    
    return best

        
def filterCdns(string,  options):
    for option in options:
        if string == option:
            return True
    return False 

def calculatesha256_sum(path):
    with open(path, 'rb') as f:
        sha256 = hashlib.sha256()
        while True:
            chunk = f.read(16 * 1024)
            if not chunk:
                break
            sha256.update(chunk)

        return sha256.hexdigest()
