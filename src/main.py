#!/usr/bin/env python3
import logging
import cli
import json
from sys import platform
from api.gog import GOGAPI
from api.wine import WineHandler
from utils.config import ConfigManager
from utils.launcher import Launcher
from utils import updates, imports
from download.manager import DownloadManager

logging.basicConfig(
    format='[%(name)s] %(levelname)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('MAIN')

def main():
    config_manager = ConfigManager()
    api_handler = GOGAPI(config_manager=config_manager)
    wine_handler = WineHandler(config_manager)
    download_manager = DownloadManager(
        config_manager=config_manager, api_handler=api_handler)

    args = cli.init_parser()
    yaml_config = config_manager.read_config_yaml()
    try:
        if (yaml_config and yaml_config.get('global').get('debug') == True) or args.debug == True:
            logger.setLevel(logging.DEBUG)
            api_handler.logger.setLevel(logging.DEBUG)
            download_manager.logger.setLevel(logging.DEBUG)
            wine_handler.logger.setLevel(logging.DEBUG)
        if args.json:
            logger.setLevel(logging.NOTSET)
            api_handler.logger.setLevel(logging.NOTSET)
            download_manager.logger.setLevel(logging.NOTSET)
            wine_handler.logger.setLevel(logging.NOTSET)
        logger.log(logging.DEBUG, args)
    except AttributeError:
        pass
    try:
        if args.command == 'auth':
            if args.option == 'login':
                api_handler.login(args.code)
            elif args.option == 'logout':
                api_handler.logout()
            elif args.option == 'show':
                api_handler.show_user()
        elif args.command == 'list-games':
            if args.sync:
                api_handler.sync_library()
            else:
                api_handler.show_library(args)
        elif args.command == 'install':
            download_manager.download(args)
        elif args.command == 'uninstall':
            print('TODO: Uninstalling')
        elif args.command == 'wine':
            if args.option == 'list':
                wine_handler.list_binaries()
            elif args.option == 'scan':
                wine_handler.find_binaries()
            elif args.option == 'select':
                args.setting = args.setting - 1
                if args.setting < 0:
                    args.setting = 0
                wine_handler.select_default(args.setting)
        elif args.command == 'launch':
            if not args.slug:
                logger.error('Specify a valid game slug')
                return
            launcher = Launcher(config_manager, wine_handler)
            launcher.start(args)
        elif args.command == 'info':
            if not args.slug:
                logger.error('Specify a valid game slug')
                return
            found_game = api_handler.find_game(query=args.slug, key='slug')
            if not found_game:
                return
            data = api_handler.get_item_data(found_game['id'])
            
            if args.json:
                print(json.dumps(data))
            else:
                print(f"*******\nTITLE: {data['title']}\nFORUM: {data['forumLink']}\nFEATURES: {json.dumps(data['features'])}\nCHANGELOG: {data['changelog']}\n*******")
        elif args.command == 'update':
            updates.check_for_updates(args,api_handler, config_manager)
        elif args.command == 'import':
            imports.import_game(args, api_handler, config_manager)

    except KeyboardInterrupt:
        pass
        logger.log(logging.WARN, 'Interupted by user. Exiting.')
        exit(0)


if platform != 'linux' and platform != 'darwin':
    logger.log(logging.ERROR, 'Currently only Linux and Mac are supported')
    exit(1)
if __name__ == '__main__':
    main()
    exit(0)