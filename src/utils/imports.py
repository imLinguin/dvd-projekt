import os
import glob
import json
import logging

def import_game(args, api_handler, config_manager):
    logger = logging.getLogger("IMPORT")
    path = args.import_path
    if not os.path.exists(path):
        logger.error("Provided path is invalid!")
        exit(1)
    logger.info("Looking for goggame-*.info file")
    game_details = load_game_details(path)

    info_file = game_details[0]
    build_id_file = game_details[1]
    platform = game_details[2]
    f = open(info_file, 'r')
    info = json.loads(f.read())
    f.close()


    logger.info(f'Found \"{info["name"]}\" platform: {platform}')
    game_id = info['gameId']
    build_id = info.get("buildId")

    # Check if user owns a game
    logger.info("Checking game ownership...")
    game = api_handler.find_game(int(game_id), "id")
    if game:
        logger.info(f"User owns {game['title']}")
    else:
        logger.info(f"User doesn't own {game['title']}, exiting...")
        exit(1)
    if build_id_file:
        f = open(build_id_file, 'r')
        build = json.loads(f.read())
        f.close()
        build_id = build.get("buildId")

    game_object = {
        'slug': game['slug'],
        'title': info['name'],
        'path': path,
        'id': game_id,
        'build_id': build_id,
        'platform': platform
    }

    installed = config_manager.read('installed')
    if not installed:
        installed = []
    for i in range(len(installed)):
        _game = installed[i]
        if _game['slug'] == game['slug'] and _game['path'] == path:
            logger.info("Game is already imported")
            exit(1)
        elif _game['slug'] == game['slug']:
            logger.info("Overriting installed earlier game")
            installed.pop(i)
            break
    installed.append(game_object)
    config_manager.save('installed', installed)
    logger.info("Written changes into the config")

def load_game_details(path):
    found = glob.glob(os.path.join(path, 'goggame-*.info'))
    build_id = None
    platform = "windows"
    if not found:
        found = glob.glob(os.path.join(path, "Contents", "Resources", 'goggame-*.info'))
        build_id = glob.glob(os.path.join(path, "Contents", "Resources", 'goggame-*.id'))
        platform='osx'
    ## TODO: Add detection for Linux titles
    return (found[0], build_id[0] if build_id else None, platform)