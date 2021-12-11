import sys
import os
from download import dl_utils
import constants

def download_movie(info, api_handler):
    data = dl_utils.get_json(api_handler, f'https://gog.com/account/movieDetails/{info["id"]}.json')
    downloads = data['downloads']
    for i in range(len(downloads)):
        download = downloads[i]
        print(f'{i+1}. Title: {download["name"]} size: {download["size"]}')
    input = ask_for_input(len(downloads))
    if not os.path.isdir(constants.DEFAULT_GAMES_PATH):
        os.makedirs(constants.DEFAULT_GAMES_PATH)

    get_file(f"https://gog.com{downloads[input]['manualUrl']}", os.path.join(constants.DEFAULT_GAMES_PATH), api_handler)
def ask_for_input(length):
    choice = input("Choose preffered download: ")

    if(choice and int(choice) and int(choice)-1 > -1 and int(choice) < length):
        return int(choice) - 1
    else:
        return ask_for_input(length)

def get_file(url, path, api_handler):
    response = api_handler.session.get(
        url, stream=True, allow_redirects=True)
    total = response.headers.get('Content-Length')
    file_name = response.url[response.url.rfind("/")+1:response.url.rfind("?")]
    path = os.path.join(path,file_name)
    downloaded = 0
    print(path)
    if os.path.exists(path):
        choice = input(f"File {path} already exists are you sure you want to continue? [y/N]: ")
        if choice.lower() == 'n' or choice.lower() == "no" or choice == '':
            return
        elif choice.lower() == 'y' or choice.lower() == 'yes':
            if os.path.exists(path):
                os.remove(path)
    with open(path, 'ab') as f:
        if total is None:
            f.write(response.content)
        else:
            total = int(total)
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                f.write(data)
                downloaded += len(data)
                progress(downloaded, total)
        f.close()

def progress(downloaded, total):
    length = 50
    done = round(downloaded/total)
    sys.stdout.write(
                f'\r[{"█" * done}{"." * (length-done)}] {done}%')
    sys.stdout.flush()