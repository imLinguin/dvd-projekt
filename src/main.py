#!/usr/bin/env python3
import logging
import argparse
from sys import platform
from api.gog import GOGAPI
from api.wine import WineHandler
from utils.config import ConfigManager
from utils.launcher import Launcher
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

    parser = argparse.ArgumentParser(description='Native CLI GOG client')
    subparsers = parser.add_subparsers(dest='command', required=True)

    auth_parser = subparsers.add_parser('auth', help='Manage authentication')
    auth_parser.add_argument('--debug', action='store_true')
    auth_parser_options = auth_parser.add_subparsers(
        dest='option', required=False)
    auth_parser_login = auth_parser_options.add_parser(
        'login', help='Allows user to authenticate')
    auth_parser_login.add_argument(
        '--code', '-c', help='Allows to directly pass a login code')
    auth_parser_options.add_parser(
        'show', help='Shows currently authenticated user')
    auth_parser_options.add_parser(
        'logout', help='Deletes cached credentials so user is logged out')

    game_list = subparsers.add_parser(
        'list-games', help="Lists games owned by user")
    game_list.add_argument(
        '--os', type=str, choices=['windows', 'macos', 'linux'])
    game_list.add_argument('--sync', action='store_true',
                           help='Forces library update')
    game_list.add_argument('--debug', action='store_true')

    install_parser = subparsers.add_parser(
        'install', help='Downloads desired selected by game slug')
    install_parser.add_argument(
        'slug', help='Slug of the game listed in list-games command')
    install_parser.add_argument(
        '--force_platform', '--platform', dest='platform', choices=['windows', 'mac', 'linux'])
    install_parser.add_argument(
        '--path', '-p', type=str, help='Specify path where to save game files')
    install_parser.add_argument(
        '--debug', action='store_true', help='Enables debug output')
    install_parser.add_argument(
        '--lang', '-l', type=str, help='Specify language e.g. en-US | pl-PL | en-UK etc.')

    comp_parser = subparsers.add_parser(
        'wine', help='Allows to change compatibility layers\' settings.')
    sub_comp_parsers = comp_parser.add_subparsers(
        dest='option', required=False)
    sub_comp_parsers.add_parser('list')
    sub_comp_parsers.add_parser('select').add_argument('setting', type=int)
    sub_comp_parsers.add_parser('scan')

    launch_parser = subparsers.add_parser('launch', help='Play specified game')
    launch_parser.add_argument(
        'slug', help='Slug of the game listed in list-games command')
    launch_parser.add_argument(
        '--prefix', type=str, help='Specify path for wine/proton prefix, default:$HOME/.wine')
    launch_parser.add_argument(
        '--gamemode', action='store_true', help='Enables gamemode when running exe file')

    args = parser.parse_args()
    yaml_config = config_manager.read_config_yaml()
    try:
        if (yaml_config and yaml_config.get('global').get('debug') == True) or args.debug == True:
            logger.setLevel(logging.DEBUG)
            api_handler.logger.setLevel(logging.DEBUG)
            download_manager.logger.setLevel(logging.DEBUG)
            wine_handler.logger.setLevel(logging.DEBUG)
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
                api_handler.show_library()
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

    except KeyboardInterrupt:
        pass
        logger.log(logging.WARN, 'Interupted by user. Exiting. Please Wait')
        download_manager.cancel()
        exit()


if platform != 'linux':
    logger.log(logging.ERROR, 'Currently only Linux supported')
    exit()
if __name__ == '__main__':
    main()
