# One file downloading functions
from download import dl_utils
import os
import sys

def get_file(url, path, api_handler, logger, ask=True):
    print(url)
    response = api_handler.session.get(
        url, stream=True, allow_redirects=True)
    total = response.headers.get('Content-Length')
    total_readable = dl_utils.get_readable_size(int(total))
    file_name = response.url[response.url.rfind("/")+1:response.url.rfind("?")]
    path = os.path.join(path,file_name)
    downloaded = 0
    if os.path.exists(path) and ask:
        logger.info("Downloading file at {path}")
        choice = input(f"File {path} already exists are you sure you want to continue? [y/N]: ")
        if choice.lower() == 'n' or choice.lower() == "no" or choice == '':
            exit(0)
        elif choice.lower() == 'y' or choice.lower() == 'yes':
            if os.path.exists(path):
                os.remove(path)
    elif os.path.exists(path) and ask == False:
        os.remove(path)

    with open(path, 'ab') as f:
        if total is None:
            f.write(response.content)
        else:
            total = int(total)
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                f.write(data)
                downloaded += len(data)
                progress(downloaded, total, total_readable)
        f.close()
    return response.ok

def progress(downloaded, total, total_readable):
    length = 50
    done = round((downloaded/total) * 50)
    current = dl_utils.get_readable_size(downloaded)

    sys.stdout.write(f'\r[{"█" * done}{"." * (length-done)}] {done*2}% {round(current[0], 2)}{current[1]}/{round(total_readable[0], 2)}{total_readable[1]}')
    sys.stdout.flush()