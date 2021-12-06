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
        gamemode = False
        prefix = ''
        envvars = ''
        try:
            config = self.config.read_config_yaml()
            if config:
                game_specific_config = config[slug]

                if config.get('global'):
                    if config['global'].get('gamemode'):
                        gamemode = config.get('global').get('gamemode')
                    if config['global'].get('prefix'):
                        prefix = config['global'].get('prefix')
                if game_specific_config:
                    if game_specific_config.get('gamemode'):
                        gamemode = game_specific_config.get('gamemode')
                    if game_specific_config.get('prefix'):
                        prefix = game_specific_config.get('prefix')
                    if game_specific_config.get('envvars'):
                        envvars = game_specific_config.get('envvars')
        except KeyError:
            pass
        if args.gamemode:
            gamemode = args.gamemode
        if args.prefix:
            prefix = args.prefix
        games_array = self.config.read('installed')
        found = None
        for game in games_array:
            if game['slug'] == slug:
                found = game
                break
        if found is None:
            self.logger.error('Game with specified slug isn\'t installed')
        game_data = self.load_game_info(found)
        task = self.get_task(game_data['playTasks'])
        exe_path = os.path.join(found['path'], task['path'])
        binary_path: str = self.wine.get_binary_path()
        prefix_path = prefix or DEFAULT_PREFIX_PATH
        prefix_path.replace(" ", "\ ")
        if not os.path.exists(prefix_path):
            os.makedirs(prefix_path)
        task_arguments = ""
        if task.get("arguments"):
            task_arguments = task['arguments']
        if binary_path.find('proton') > 0:
            command = f'{"gamemoderun" if gamemode == True else ""} {envvars} STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.steam STEAM_COMPAT_DATA_PATH="{prefix_path}" "{binary_path}" run "{exe_path}" {task_arguments}'
        else:
            command = f'{"gamemoderun" if gamemode == True else ""} {envvars} WINEPREFIX="{prefix_path}" "{binary_path}" "{exe_path}" {task_arguments}'
        command = command.strip()
        print("Issuing command\n", command)
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
        if(len(tasks) == 1):
            return tasks[0]
        prompt = "Choose a task:\n"
        for task in range(len(tasks)):
            prompt += f'{task+1}. {tasks[task]["name"]}\n'
        choice = input(prompt)
        if not (int(choice)-1 < len(tasks) and int(choice)-1 > 0):
            return self.get_task(tasks)
        return tasks[int(choice)-1]
