import requests
import webbrowser
import logging
import time
import json



_gog_auth_url = 'https://auth.gog.com/auth?client_id=46899977096215655&redirect_uri=https://embed.gog.com/on_login_success?origin=client&response_type=code&layout=client2'
_gog_new_token_url = 'https://auth.gog.com/token?client_id=46899977096215655&client_secret=9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9&grant_type=authorization_code&redirect_uri=https://embed.gog.com/on_login_success?origin=client'
_gog_refresh_token_url = 'https://auth.gog.com/token?client_id=46899977096215655&client_secret=9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9&grant_type=refresh_token'
_gog_user_data_url = 'https://embed.gog.com/userData.json'
_gog_library_url = 'https://embed.gog.com/account/getFilteredProducts?'


class GOGAPI():
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger('API')
    def _save_to_config(self, response):
        jsonData = response.json()
        expires_in = jsonData['expires_in']
        jsonData["expire_time"] = time.time() + int(expires_in)
        self.config.save('user', jsonData)

    def is_expired(self):
        return self.config.get('user', 'expire_time') < time.time()

    def _refresh_token(self):
        token = self.config.get('user', 'refresh_token')
        if token:
            self.logger.log(logging.INFO, msg='Trying to refresh token')
            response = requests.get(
                f'{_gog_refresh_token_url}&refresh_token={token}')
            self.logger.log(logging.DEBUG, response.text)
            if response.ok:
                self.logger.log(logging.INFO, msg='Token successfully refreshed')
                self._save_to_config(response)
                self.get_user_data()
            else:
                self.logger.log(
                    logging.ERROR, msg='Error refreshing token, try authenticating again')

    def _get_new_token(self, code: str):
        if not code:
            return False
        response = requests.get(_gog_new_token_url+f'&code={code}')
        if not response.ok:
            return False
        self.logger.log(logging.INFO, msg='Authentication successful')
        self._save_to_config(response)
        self.get_user_data()
        return True

    def get_user_data(self):
        response = requests.get(_gog_user_data_url, headers={
                                'Authorization': f'Bearer {self.config.get("user", "access_token")}'})

        if response.ok:
            data = response.json()
            self.config.set_data('user', 'username', data['username'])
            self.config.set_data('user', 'avatar', data['avatar'])
            return True

    def sync_library(self):
        if self.is_expired():
            self._refresh_token()
        default_args = 'mediaType=1&hiddenFlag=0'
        response = requests.get(_gog_library_url+default_args, headers={
                                'Authorization': f'Bearer {self.config.get("user", "access_token")}'})
        self.logger.log(logging.DEBUG, response)
        if response.ok:
            self.config.save('library', response.json()['products'])
            self.logger.log(logging.INFO, 'Library refreshed')
        else:
            self.logger.log(logging.ERROR, f'Error syncing library, response for debuging: {response.text}')

    def show_library(self):
        array = self.config.read('library')
        total = len(array)

        for game in array:
            title = game['title']
            windows_support = game['worksOn']['Windows']
            macos_support = game['worksOn']["Mac"]
            linux_support = game['worksOn']["Linux"]
            media_type = 'movie' if game['isMovie'] else 'game'
            platforms = []
            if linux_support:
                platforms.append('Linux')
            if macos_support:
                platforms.append('Mac')
            if windows_support:
                platforms.append('Windows')
            print(f'* [{title}] support:{",".join(platforms)} type:{media_type}')
        print(f'** Total: {total} **')

    def login(self, code: str = None):
        if not code:
            self.logger.log(
                logging.INFO, msg='No code passed, opening browser for manual input')
            webbrowser.open(_gog_auth_url)
            code = input('Provide code seen in URL: ')
            if not code:
                return False
        if not self._get_new_token(code):
            self.logger.log(logging.ERROR, msg='Code is invalid')
            return False

    def logout(self):
        self.config.logout_clean()
        self.logger.log(logging.INFO, 'Successfuly logged out')

    def show_user(self):
        username = self.config.get('user', 'username')
        avatar = self.config.get('user', 'avatar')

        self.logger.log(
            logging.INFO, f'Showcase of user information\nUsername: {username}\nAutentication status: {"expired" if is_expired else "valid"}\nAvatarURL: {avatar}.png')
