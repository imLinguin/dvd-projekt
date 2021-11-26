import requests
import webbrowser
import logging
import time
import json
import constants
from multiprocessing import cpu_count

_gog_auth_url = f'{constants.GOG_AUTH}/auth?client_id=46899977096215655&redirect_uri={constants.GOG_EMBED}/on_login_success?origin=client&response_type=code&layout=client2'
_gog_new_token_url = f'{constants.GOG_AUTH}/token?client_id=46899977096215655&client_secret=9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9&grant_type=authorization_code&redirect_uri=https://embed.gog.com/on_login_success?origin=client'
_gog_refresh_token_url = f'{constants.GOG_AUTH}/token?client_id=46899977096215655&client_secret=9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9&grant_type=refresh_token'
_gog_user_data_url = f'{constants.GOG_EMBED}/userData.json'
_gog_library_url = f'{constants.GOG_EMBED}/account/getFilteredProducts?'
_gog_item_data_url = f'{constants.GOG_EMBED}/account/gameDetails/'


class GOGAPI():
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger('API')
        self.session = requests.sessions.Session()
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=cpu_count())
        self.session.mount("https://", adapter)
        self.auth_status = self.get_auth_status()
        self._refresh_session()

    def _save_to_config(self, response):
        jsonData = response.json()
        expires_in = jsonData['expires_in']
        jsonData["expire_time"] = time.time() + int(expires_in)
        self.config.save('user', jsonData)

    def _refresh_session(self):
        self.session.headers = {
            'Authorization': f'Bearer {self.config.get("user", "access_token")}', 'User-Agent': 'dvdProjekt Linux client'}

    def is_expired(self):
        return self.auth_status and self.config.get('user', 'expire_time') < time.time()

    def _refresh_token(self):
        token = self.config.get('user', 'refresh_token')
        if token:
            self.logger.info('Trying to refresh token')
            response = self.session.get(
                f'{_gog_refresh_token_url}&refresh_token={token}')
            if response.ok:
                self.logger.info('Token successfully refreshed')
                self._save_to_config(response)
                self._refresh_session()
                self.get_user_data()
                return True
            else:
                self.logger.error('Error refreshing token, try authenticating again')
                return False

    def _get_new_token(self, code: str):
        if not code:
            return False
        response = self.session.get(_gog_new_token_url+f'&code={code}')
        if not response.ok:
            return False
        self.logger.info('Authentication successful')
        self._save_to_config(response)
        self._refresh_session()
        self.get_user_data()
        return True

    def get_user_data(self):
        response = self.session.get(_gog_user_data_url, headers={
            'Authorization': f'Bearer {self.config.get("user", "access_token")}'})

        if response.ok:
            data = response.json()
            self.config.set_data('user', 'username', data['username'])
            self.config.set_data('user', 'avatar', data['avatar'])
            return True

    def sync_library(self):
        if self.is_expired():
            self._refresh_token()
        if not self.auth_status:
            self.logger.error('You are not logged in')
            return
        args = 'mediaType=1&hiddenFlag=0&sortBy=title'
        response = self.session.get(_gog_library_url+args, headers={
            'Authorization': f'Bearer {self.config.get("user", "access_token")}'})
        self.logger.log(logging.DEBUG, response)
        if response.ok:
            self.config.save('library', response.json()['products'])
            self.logger.info( 'Library refreshed')
        else:
            self.logger.error(f'Error syncing library, response for debuging: \n{response.text}')

    def show_library(self):
        array = self.config.read('library')
        total = len(array)

        for game in array:
            title = game['title']
            windows_support = game['worksOn']['Windows']
            macos_support = game['worksOn']["Mac"]
            linux_support = game['worksOn']["Linux"]
            slug = game['slug']
            media_type = 'movie' if game['isMovie'] else 'game'
            platforms = []
            if linux_support:
                platforms.append('Linux')
            if macos_support:
                platforms.append('Mac')
            if windows_support:
                platforms.append('Windows')
            print(
                f'* [{title}] slug:{slug} support:{",".join(platforms)} type:{media_type}')
        print(f'** Total: {total} **')

    def find_game(self, query: str, key: str):
        items: list = self.config.read('library')
        found = None
        for item in items:
            if item[key] == query:
                found = item
                break
        if found:
            return found
        else:
            self.logger.error('Invalid slug')
            return None

    def get_item_data(self, id):
        if self.is_expired():
            if not self._refresh_token():
                return
        url = _gog_item_data_url+f'{id}.json'
        response = self.session.get(url, headers={
            'Authorization': f'Bearer {self.config.get("user", "access_token")}'})
        self.logger.debug(url)
        if response.ok:
            return response.json()

    def login(self, code: str = None):
        if not code:
            self.logger.info('No code passed, opening browser for manual input')
            webbrowser.open(_gog_auth_url)
            code = input('Provide code seen in URL: ')
            if not code:
                return False
        if not self._get_new_token(code):
            self.logger.error('Code is invalid')
            return False
        else:
            self.sync_library()

    def logout(self):
        if self.config.logout_clean():
            self.logger.info('Successfuly logged out')
        else:
            self.logger.error('Something went wrong')

    def show_user(self):
        username = self.config.get('user', 'username')
        avatar = self.config.get('user', 'avatar')

        self.logger.info(
            f'Showcase of user information\nUsername: {username}\nAutentication status: {"expired" if self.is_expired() else "valid"}\nAvatarURL: {avatar}.png')

    def get_auth_status(self):
        return self.config.get('user', 'access_token') is not None
