import sys
import os
from download import dl_utils, file_dl
import constants
import logging

def download_movie(info, api_handler):
    logger = logging.getLogger("MOVIE")
    data = dl_utils.get_json(api_handler, f'https://gog.com/account/movieDetails/{info["id"]}.json')
    downloads = data['downloads']
    for i in range(len(downloads)):
        download = downloads[i]
        print(f'{i+1}. Title: {download["name"]} size: {download["size"]}')
    input = ask_for_input(len(downloads))
    if not os.path.isdir(constants.DEFAULT_GAMES_PATH):
        os.makedirs(constants.DEFAULT_GAMES_PATH)
    file_dl.get_movie(f"https://gog.com{downloads[input]['manualUrl']}", os.path.join(constants.DEFAULT_GAMES_PATH), api_handler, logger, True)

def ask_for_input(length):
    choice = input("Choose preffered download: ")
    if(choice and int(choice) and int(choice)-1 > -1 and int(choice) < length):
        return int(choice) - 1
    else:
        return ask_for_input(length)