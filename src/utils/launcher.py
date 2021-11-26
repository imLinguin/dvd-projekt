import json
import logging
import os
import subprocess
from constants import DEFAULT_PREFIX_PATH


class Launcher():
    def __init__(self, config_manager, wine_handler):
        self.config = config_manager
        self.wine = wine_handler
        self.logger = logging.getLogger('LAUNCHER')
        self.logger.setLevel(logging.INFO)

    def start(self, args):
        slug = args.slug
        gamemode = args.gamemode
        prefix = args.prefix

        games_array = self.config.read('installed')
        found = None
        for game in games_array:
            if game['slug'] == slug:
                found = game
                break
        if found is None:
            self.logger.error('Game with specified slug isn\'t installed')
            return
        game_data = self.load_game_info(found)
        task = self.get_task(game_data['playTasks'])
        exe_path = os.path.join(found['path'], task['path'])
        binary_path: str = self.wine.get_binary_path()
        prefix_path = args.prefix or DEFAULT_PREFIX_PATH
        prefix_path.replace(" ", "\ ")
        os.makedirs(prefix_path)
        if binary_path.find('proton'):
            command = f'{"gamemoderun" if gamemode == True else ""} STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.steam STEAM_COMPAT_DATA_PATH="{prefix_path}" "{binary_path}" run "{exe_path}" {task["arguments"]}'
        else:
            command = f'{"gamemoderun" if gamemode == True else ""} WINEPREFIX="{prefix_path}" "{binary_path}" "{exe_path}" {task["arguments"]}'
        command = command.strip()
        print(command)
        subprocess.run(command, shell='/bin/sh', cwd=found['path'])

    def load_game_info(self, game):
        filename = f'goggame-{game["id"]}.info'
        abs_path = os.path.join(game['path'], filename)
        self.logger.info(f'Loading gameinfo {filename} file')
        with open(abs_path) as f:
            data = f.read()
            f.close()
            return json.loads(data)

    def get_task(self, tasks: list):
        prompt = "Choose a task:\n"
        for task in range(len(tasks)):
            prompt += f'{task+1}. {tasks[task]["name"]}\n'
        choice = input(prompt)
        if not (int(choice)-1 < len(tasks) and int(choice)-1 > 0):
            return self.get_task(tasks)
        return tasks[int(choice)-1]
