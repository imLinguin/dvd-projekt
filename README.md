<p style="display:flex; justify-content:center;">
    <img src="./content/project_tux.svg" width=600px>
</p>

## DISCLAIMER
Script isn't ready yet. I'm actively working on it.


## Features
- [x] Download native Windows titles (TODO: multithreaded downloading)
- [x] Play native Windows titles through Wine/Proton
- [ ] Download native Linux installers from GOG
- [ ] Keep games updated
- [ ] Download DLCs
- [ ] Manage downloaded games

## Running
Script isn't ready for distributing yet, however if you really want to try it out you should clone the repo (`git clone https://github.com/imLinguin/dvd-projekt` or Download the ZIP) and just run the `src/main.py` file.

## Positional arguments:
- auth - Manage authentication
- list-games - Lists games owned by user
- install - Downloads desired selected by game slug
- wine - Allows to change compatibility layers' settings.
- launch - Play specified game

## Configuration
Script supports configuration in a text file. Which is located under `$HOME/.config/dvdProjekt/config.yaml`
When `$XDG_CONFIG_HOME` variable is present path looks like this `$XDG_CONFIG_HOME/dvdProjekt/config.yaml`

You can specify config for each game differently or globally


### Priority of config:
  1. Command Line as arguments
  2. Game specific
  3. Global

### Example
```yaml
global: # global config
  gamemode: true #
  debug: true #Enables debug level of logging
  lang: 'pl-PL'
  prefix: '/home/linguin/Games/dvdProjekt/prefix' # Prefix location

ghostrunner: # slug of the game
  envvars: 'PROTON_ENABLE_NVAPI=1 VKD3D_CONFIG=dxr' # Enviroment variables to be passed when launching the game
  prefix: '/home/linguin/Games/dvdProjekt/ghost_runner_prefix' # Prefix for that game only
```

### Made in Poland 🇵🇱