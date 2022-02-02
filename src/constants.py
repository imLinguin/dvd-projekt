import os


GOG_CDN = 'https://cdn.gog.com'
GOG_CONTENT_SYSTEM = 'https://content-system.gog.com'
GOG_EMBED = 'https://embed.gog.com'
GOG_AUTH = 'https://auth.gog.com'
GOG_API = 'https://api.gog.com'
DEPENDENCIES_URL = 'https://content-system.gog.com/dependencies/repository?generation=2'
DEPENDENCIES_V1_URL = 'https://content-system.gog.com/redists/repository'

DEFAULT_GAMES_PATH = os.path.join(os.getenv('HOME'), 'Games', 'dvdProjekt')
DEFAULT_PREFIX_PATH = os.path.join(os.getenv('HOME'), '.wine')
CACHE_PATH = os.path.join(os.getenv('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'dvdProjekt')
CONFIG_PATH = os.path.join(os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'dvdProjekt')
# Allowed CDN list others might cause problems (Needs more testing)
GALAXY_CDNS = ["edgecast", "high_winds", "lumen"]