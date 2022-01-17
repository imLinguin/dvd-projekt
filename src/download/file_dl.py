# One file downloading functions
from download import dl_utils
import os
import sys

def get_file(url, path, api_handler, logger=None, ask=True):
    response = api_handler.session.get(
        url, stream=True, allow_redirects=True)
    total = response.headers.get('Content-Length')
    total_readable = dl_utils.get_readable_size(int(total))
    file_name = response.url[response.url.rfind("/")+1:response.url.rfind("?")]
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    path = os.path.join(path,file_name)
    downloaded = 0
    if os.path.exists(path) and ask:
        choice = input(f"File {path} already exists are you sure you want to continue? [y/N]: ")
        if choice.lower() == 'n' or choice.lower() == "no" or choice == '':
            exit(0)
        elif choice.lower() == 'y' or choice.lower() == 'yes':
            if os.path.exists(path):
                os.remove(path)
    elif os.path.exists(path) and ask == False:
        os.remove(path)
    logger.info(f"Downloading file at {path}")

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
    sys.stdout.write('\n')
    sys.stdout.flush()
    return [response.ok, path]

def progress(downloaded, total, total_readable):
    length = 50
    done = round((downloaded/total) * 50)
    current = dl_utils.get_readable_size(downloaded)

    sys.stdout.write(f'\r[{"█" * done}{"." * (length-done)}] {done*2}% {current[0]:.02f}{current[1]}/{total_readable[0]:.02f}{total_readable[1]}')
    sys.stdout.flush()