import logging
import argparse
from sys import platform
from api.gog import GOGAPI
from utils.config import ConfigManager
from utils.download_manager import DownloadManager

logging.basicConfig(
    format='[%(name)s] %(levelname)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('MAIN')


def main():
    config_manager = ConfigManager()
    api_handler = GOGAPI(config_manager=config_manager)
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
        'slug', help='Slug of the game listed in list_games command')
    install_parser.add_argument(
        '--force-platform', '--platform', dest='platform', choices=['windows', 'mac', 'linux'])
    install_parser.add_argument('--path', '-p', type=str)
    install_parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        api_handler.logger.setLevel(logging.DEBUG)
        download_manager.logger.setLevel(logging.DEBUG)
    logger.log(logging.DEBUG, args)
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
            download_manager.init_download(args)
    except KeyboardInterrupt:
        logger.log(logging.WARN, 'Interupted by user exiting')
        exit()


if platform != 'linux':
    logger.log(logging.ERROR, 'Currently only Linux supported')
    exit()
if __name__ == '__main__':
    main()
