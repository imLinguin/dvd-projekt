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
        builds = dl_utils.get_json(api_handler, f'{constants.GOG_CONTENT_SYSTEM}/products/{game["id"]}/os/{game["platform"]}/builds?generation=2')
        if builds['items'][0]['build_id'] != build_id:
            found += 1
            logger.info(f"Update available for {game['title']}")
    if found == 0:
        logger.info(f"No updates available")

def read_build_id(game):
    build_id_file = ""
    goggame = f'goggame-{game["id"]}'
    if game['platform'] == 'windows':
        build_id_file = os.path.join(game['path'], f"{goggame}.info")
    elif game['platform'] == 'osx':
        build_id_file = os.path.join(game['path'], 'Contents', 'Resources', f"{goggame}.id")
    # TODO: Linux titles detection
    
    f = open(build_id_file, 'r')
    game_data = f.read()
    data = json.loads(game_data)
    f.close()

    return data["buildId"]
