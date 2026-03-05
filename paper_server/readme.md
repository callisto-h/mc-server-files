Folder structure for paper server (the server root) and velocity proxy.

To install the requirements for the velocity proxy:
- make a python venv (`python3 -m venv .venv`)
- activate with `source .venv/bin/activate`
- install the python packages from `requirements.txt` with 
  `pip3 install -r requirements.txt`. Then deactivate with
  `deactivate`. 

To run the proxy, execute `start.sh` from `/velocity_proxy`. It will handle
launching the server as long as the directory structure remains intact. It
will also launch the heartbeat service which connects to the discord bot.

To add somebody to the server, execute `add_player.sh` from `/velocity_proxy`
and paste the command into the velocity terminal.

Read the config files or drop them into an LLM and ask for an explanation.

- Callisto

.
├── paper_server
│   ├── backups
│   ├── banned-ips.json
│   ├── banned-players.json
│   ├── bukkit.yml
│   ├── cache
│   ├── commands.yml
│   ├── config
│   ├── config.yml
│   ├── crash-reports
│   ├── eula.txt
│   ├── help.yml
│   ├── libraries
│   ├── logs
│   ├── ops.json
│   ├── paper-1.21.11-116.jar
│   ├── permissions.yml
│   ├── plugins
│   ├── readme.md
│   ├── server.properties
│   ├── spigot.yml
│   ├── start_server.sh
│   ├── usercache.json
│   ├── version_history.json
│   ├── versions
│   ├── wepif.yml
│   ├── whitelist.json
│   ├── world
│   ├── world_nether
│   └── world_the_end
└── velocity_proxy
    ├── add_player.sh
    ├── forwarding.secret
    ├── heartbeat.py
    ├── lang
    ├── logs
    ├── plugins
    ├── requirements.txt
    ├── start.sh
    ├── velocity-3.5.0-SNAPSHOT-576.jar
    ├── velocity.toml
    └── whitelist_user_command.txt
