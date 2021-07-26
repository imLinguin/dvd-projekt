import logging
import argparse
from api.gog import GOGAPI
from utils.config import ConfigManager

logging.basicConfig(
    format='[%(name)s] %(levelname)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('MAIN')


def main():
    config_manager = ConfigManager()
    apiHandler = GOGAPI(config_manager=config_manager)

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
    game_list.add_argument('--sync', action='store_true', help='Forces library update')
    game_list.add_argument('--debug', action='store_true')

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.log(logging.DEBUG, args)

    if args.command == 'auth':
        if args.option == 'login':
            apiHandler.login(args.code)
        elif args.option == 'logout':
            apiHandler.logout()
        elif args.option == 'show':
            apiHandler.show_user()
    elif args.command == 'list-games':
        # Listing games
        if args.sync:
            apiHandler.sync_library()
        else:
            apiHandler.show_library()

if __name__ == '__main__':
    main()
