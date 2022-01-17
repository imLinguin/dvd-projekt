from download import file_dl, dl_utils
import os
import shutil
import constants
import subprocess
import logging

def download(data, api_handler, path, config):
    logger = logging.getLogger("LINUX")
    downloads = []
    helper = 0
    languagesList = 'Pick the language: \n'
    for download in data['downloads']:
        language = download[0]
        installerUrl = download[1]['linux'][0]['manualUrl']
        downloads.append({
            "language":language,
            "url":installerUrl
        })
        languagesList += f'{helper+1}. {language}\n'
    choice = 0
    if len(downloads) > 1:
        choice = ask_for_input(languagesList, len(downloads))
    url = f'{constants.GOG_EMBED}/{downloads[choice]["url"]}'
    download_path = constants.CACHE_PATH
    downloader = file_dl.get_file(url, download_path, api_handler, logger=logger, ask=False)

    if not downloader[0]:
        logger.error("Error downloading installer. Try again")
        return
    
    script_path = downloader[1]
    tmp_path = os.path.join(constants.CACHE_PATH, 'gameData')
    status = unpack_installer(script_path, tmp_path, logger)
    if not status:
        logger.error("Unpacking failed. Please try again")
        return
    tmp_game_data_path = os.path.join(tmp_path, 'data', 'noarch')
    logger.info("Moving game data")
    shutil.move(tmp_game_data_path, path)
    logger.info(f"Data moved to {path}")

    gameinfo_path = os.path.join(path, 'gameinfo')

    gameinfo = open(gameinfo_path, 'r').read()

    version = gameinfo.split('\n')[1]

    installed_games = config.read('installed')
    if not installed_games:
        installed_games = []
    gameobj = {'slug': data['slug'],
                'title': data['title'], 'path': path, 'id': data['id'], 'build_id': version, 'platform': 'linux'}
    added = False
    for igame in range(len(installed_games)):
        if installed_games[igame]['slug'] == gameobj['slug']:
            installed_games[igame] = gameobj
            added = True
            break
    if not added:
        installed_games.append(gameobj)
    config.save('installed', installed_games)
    logger.info('Download complete. Cleaning up')

    os.remove(script_path)
    shutil.rmtree(tmp_path)


def unpack_installer(script_path, target_path, logger):
    logger.info("Unpacking installer using unzip")
    if os.path.exists(target_path):
        shutil.rmtree(target_path)
    command = ['unzip', '-qq', script_path, '-d', target_path]

    process = subprocess.Popen(command)
    return_code = process.wait()
    return return_code == 1


def ask_for_input(msg, length):
    value = input(msg)
    value = int(value)
    if value is not None:
        value -= 1
        if value >= 0 and value <= length:
            return value
        else:
            return ask_for_input(msg, length)
    else:
        return ask_for_input(msg, length)

