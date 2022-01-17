import os
import json
import constants
import logging
from download import dl_utils

def check_for_updates(args, api_handler, config_manager):
    if(api_handler.is_expired()):
        api_handler._refresh_token()
    logger = logging.getLogger("UPDATER")
    installed_games = config_manager.read('installed')
    if not installed_games:
        logger.error("No games installed")
        exit(1)
    found = 0
    for game in installed_games:
        build_id = read_build_id(game)
        logger.info(f"Checking for updates of {game['title']}")
        if game['platform'] != 'linux':
            builds = dl_utils.get_json(api_handler, f'{constants.GOG_CONTENT_SYSTEM}/products/{game["id"]}/os/{game["platform"]}/builds?generation=2')
            if builds['items'][0]['build_id'] != build_id:
                found += 1
                logger.info(f"Update available for {game['title']}")
        else:
            data = api_handler.get_item_data(game['id'])
            new_version = data['downloads'][0][1]['linux'][0]['version']
            if build_id != new_version:
                found += 1
                logger.info(f"Update available for {game['title']}")
    if found == 0:
        logger.info(f"No updates available")

def read_build_id(game):
    build_id_file = ""
    goggame = f'goggame-{game["id"]}'
    if game['platform'] == 'windows':
        build_id_file = os.path.join(game['path'], f"{goggame}.id")
        if not os.path.exists(build_id_file):
            build_id_file = os.path.join(game['path'], f"{goggame}.info")
    elif game['platform'] == 'osx':
        build_id_file = os.path.join(game['path'], 'Contents', 'Resources', f"{goggame}.id")
    elif game['platform'] == 'linux':
        build_id_file = os.path.join(game['path'], 'gameinfo')
        version = open(build_id_file, 'r').read().split('\n')[1]
        return version
    # TODO: Linux titles detection
    print(build_id_file)
    f = open(build_id_file, 'r')
    game_data = f.read()
    data = json.loads(game_data)
    f.close()
    return data["buildId"]
