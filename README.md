# Tuesday Night Gaming — Minecraft Server

## Directory structure

```
minecraft/
├── docker-compose.yml
├── .env                        ← secrets, never commit this
├── add_player.sh               ← run on host to whitelist a player
├── controller/
│   ├── Dockerfile
│   ├── controller.py
│   └── requirements.txt
├── velocity/
│   ├── Dockerfile
│   ├── start.sh
│   ├── start_server.sh
│   ├── heartbeat.py
│   ├── requirements.txt
│   ├── velocity.toml
│   ├── forwarding.secret
│   └── plugins/
└── paper/
    ├── Dockerfile
    ├── server.properties       ← enable RCON here
    ├── whitelist.json
    ├── plugins/
    ├── world/
    ├── world_nether/
    └── world_the_end/
```

## First time setup

1. Copy your existing paper_server and velocity_proxy files into paper/ and velocity/

2. Enable RCON in paper/server.properties:
   ```
   enable-rcon=true
   rcon.port=25575
   rcon.password=<match RCON_PASSWORD in .env>
   ```

3. Fill in .env with your secrets

4. Build and start:
   ```sh
   docker compose up -d controller
   docker compose up -d velocity
   # Paper is started on demand by vane-velocity
   ```

## Common commands

Start everything:
```sh
docker compose up -d controller velocity
```

View Velocity console:
```sh
docker attach minecraft-velocity-1
# Detach: Ctrl+P then Ctrl+Q
```

View Paper console:
```sh
docker attach minecraft-paper-1
# Detach: Ctrl+P then Ctrl+Q
```

View logs:
```sh
docker logs -f minecraft-velocity-1
docker logs -f minecraft-paper-1
docker logs -f minecraft-controller-1
```

Add a player:
```sh
./add_player.sh knite6300
```

Check status:
```sh
curl http://localhost:5000/health
```

Stop everything:
```sh
docker compose down
```
