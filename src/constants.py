import os


GOG_CDN = 'https://cdn.gog.com'
GOG_CONTENT_SYSTEM = 'https://content-system.gog.com'
GOG_EMBED = 'https://embed.gog.com'
GOG_AUTH = 'https://auth.gog.com'
DEFAULT_GAMES_PATH = os.path.join(os.getenv('HOME'), 'Games', 'dvdProjekt')
DEFAULT_PREFIX_PATH = os.path.join(os.getenv('HOME'), '.wine')
CONFIG_PATH = os.path.join(os.getenv('XDG_CONFIG_HOME'), '.config', 'dvdProjekt') if os.getenv(
    'XDG_CONFIG_HOME') is not None else os.path.join(os.getenv("HOME"), '.config', 'dvdProjekt')
