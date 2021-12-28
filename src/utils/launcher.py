import json
import logging
import os
import subprocess
from sys import platform
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
        task_path = task['path'].replace("\\\\","/")
        exe_path = os.path.join(found['path'], task['path'])
        binary_path: str = self.wine.get_binary_path()
        prefix_path = prefix or DEFAULT_PREFIX_PATH
        prefix_path.replace(" ", "\ ")
        if not os.path.exists(prefix_path):
            os.makedirs(prefix_path)
        task_arguments = ""
        if task.get("arguments"):
            task_arguments = task['arguments']

        if platform == 'linux':
            if found['platform'] == 'windows':
                if binary_path.find('proton') > 0:
                    command = f'{"gamemoderun" if gamemode == True else ""} {envvars} STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.steam/steam STEAM_COMPAT_DATA_PATH="{prefix_path}" "{binary_path}" run "{exe_path}" {task_arguments}'
                else:
                    command = f'{"gamemoderun" if gamemode == True else ""} {envvars} WINEPREFIX="{prefix_path}" "{binary_path}" "{exe_path}" {task_arguments}'
            elif found['platform'] == 'osx':
                self.unsupported_platform()

        elif platform == 'darwin':
            if found['platform'] == 'darwin':
                command = f'{envvars} {exe_path} {task_arguments}'
            else:
                self.unsupported_platform()

        elif platform == 'win32':
            if found['platform'] == 'win32':
                command = f'{envvars} {exe_path} {task_arguments}'
            else:
                self.unsupported_platform()

            
        command = command.strip()
        print("Issuing command\n", command)

        process = subprocess.run(command, shell=True, cwd=found['path'])

        exit(process.returncode)

    def load_game_info(self, game):
        filename = f'goggame-{game["id"]}.info'
        abs_path = os.path.join(game['path'], filename) if platform != "darwin" else os.path.join(game['path', 'Contents', 'Resources', filename])
        self.logger.info(f'Loading game info from {abs_path}')
        if not os.path.isfile(abs_path):
            self.logger.error('File does not exist. Exiting...')
            exit(1)
        with open(abs_path) as f:
            data = f.read()
            f.close()
            return json.loads(data)

    def get_task(self, tasks: list):
        
        prompt = "Choose a task:\n"
        count = 0
        playable_tasks = []
        for task in range(len(tasks)):
            if tasks[task]["category"] == "game" or tasks[task]["category"] == "launcher":
                playable_tasks.append(tasks[task])
        if(len(playable_tasks) == 1):
            return playable_tasks[0]
        for task in range(len(playable_tasks)):
            prompt += f'{task+1}. {playable_tasks[task]["name"]}\n'
            
        count = len(playable_tasks)
        choice = input(prompt)
        if not (int(choice)-1 < count and int(choice)-1 >= 0):
            return self.get_task(tasks)
        return tasks[int(choice)-1]

    def unsupported_platform(self):
        self.logger.error('Unsupported platform!')
        exit(1)