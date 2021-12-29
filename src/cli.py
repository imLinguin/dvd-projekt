import argparse
def init_parser():
    parser = argparse.ArgumentParser(description='Welcome to dvd-projekt Native GOG client for Linux and MacOS')
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
    game_list.add_argument('--json', action='store_true', help='Prints response as JSON')
    game_list.add_argument('--debug', action='store_true')

    install_parser = subparsers.add_parser(
        'install', help='Downloads desired selected by game slug')
    install_parser.add_argument(
        'slug', help='Slug of the game listed in list-games command')
    install_parser.add_argument(
        '--force_platform', '--platform', dest='platform', choices=['windows', 'osx', 'linux'])
    install_parser.add_argument(
        '--path', '-p', type=str, help='Specify path where to save game files')
    install_parser.add_argument(
        '--debug', action='store_true', help='Enables debug output')
    install_parser.add_argument(
        '--lang', '-l', type=str, help='Specify language e.g. en-US | pl-PL etc.')

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

    info_parser = subparsers.add_parser(
        "info", help="Get info about specified game")
    info_parser.add_argument("--debug", action='store_true', help="Enables Debug console logging")
    info_parser.add_argument("--json", action="store_true", help="Returns json formated data")
    info_parser.add_argument("slug", help='Slug of the game listed in list-games command')

    updates_parser = subparsers.add_parser("update", help="Checks for games updates")
    updates_parser.add_argument("--debug", action='store_true', help="Enables Debug console logging")
    
    import_parser = subparsers.add_parser("import", help="Import already installed GOG game")
    import_parser.add_argument("--debug", action='store_true', help="Enables Debug console logging")
    import_parser.add_argument("import_path", help="Path where game is installed")


    return parser.parse_args()