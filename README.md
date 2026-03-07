# Tuesday Night Gaming — Minecraft Server

By Callisto
For my friends

---

## Architecture

The server is made up of four Docker containers orchestrated by `docker-compose`:

```
Internet
    │
    ▼
┌─────────────┐        ┌──────────────┐
│   Velocity  │───────▶│    Paper     │
│  :25565     │        │  :25575      │
│  (proxy)    │        │  (game)      │
└──────┬──────┘        └──────────────┘
       │
       │ POST /start, /whitelist
       ▼
┌─────────────┐
│ Controller  │───▶ Docker socket
│  :5000      │     (starts/stops Paper)
└─────────────┘

┌─────────────┐
│  Squaremap  │  serves static map files from paper_server/plugins/squaremap/web
│  :8080      │  (nginx, read-only mount, no connection to Paper)
└─────────────┘
```

**Velocity** is the only internet-facing process. It handles player connections on port 25565 and uses the vane-velocity plugin to start Paper on demand when a player connects, and shut it down after 15 minutes empty.

**Paper** runs on an internal Docker network only. It is never exposed directly to the internet. Modern forwarding is used to pass real Mojang UUIDs from Velocity to Paper.

**Controller** is a small Flask app that has access to the Docker socket. It is the only container that can start or stop Paper. It also handles player whitelisting — looking up UUIDs from the Mojang API, running `whitelist add` on Paper via docker exec, and granting LuckPerms permissions on Velocity via docker exec. It exposes port 5000 to the host only.

**Squaremap** serves the live map as a static nginx container. It has no runtime connection to Paper — it simply reads files that Paper writes to disk.

**Heartbeat** is a Python script that runs inside the Velocity container. Every 60 seconds it checks the player count and POSTs to a Fly.io-hosted Discord bot, which updates the bot's presence to show server status and player count.

---

## Directory Structure

```
mc-server-files/
├── docker-compose.yml       # orchestrates all containers
├── .env                     # secrets (not in repo — see Secrets section)
├── add_player.sh            # run on host to whitelist a player
├── backup.sh                # run on host to back up world files
├── controller/
│   ├── Dockerfile
│   ├── controller.py        # Flask app — manages Paper container + whitelisting
│   └── requirements.txt
├── velocity_proxy/
│   ├── Dockerfile
│   ├── start.sh             # starts heartbeat then Velocity
│   ├── start_server.sh      # called by vane-velocity — POSTs to controller /start
│   ├── heartbeat.py         # sends status to Discord bot on Fly.io
│   ├── requirements.txt
│   ├── velocity.toml        # proxy config
│   ├── forwarding.secret    # NOT in repo — see Secrets section [!IMPORTANT!]
│   └── plugins/
└── paper_server/
    ├── Dockerfile
    ├── start.sh             # starts Paper
    ├── server.properties
    ├── plugins/
    ├── whitelist.json
    ├── world/               # NOT in repo — restore from Google Drive
    ├── world_nether/        # NOT in repo — restore from Google Drive
    └── world_the_end/       # NOT in repo — restore from Google Drive
```

---

## Secrets

The following secrets are **not included in this repo** and must be populated before running:

**`.env`** (create at repo root):
```sh
# Fly.io Discord bot
HEARTBEAT_KEY=your_heartbeat_key_here
FLY_URL=https://mc-server-bot.fly.dev/heartbeat
```

Generate secure values with:
```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**`velocity_proxy/forwarding.secret`** — the shared secret used for Velocity modern forwarding. Must match the value in `paper_server/config/paper-global.yml` under `proxies.velocity.secret`. Generate with:
```sh
openssl rand -base64 32 > velocity_proxy/forwarding.secret
```

Then update `paper_server/config/paper-global.yml`:
```yaml
proxies:
  velocity:
    enabled: true
    online-mode: false
    secret: "your-secret-here"
```

---

## Running the Server

### Prerequisites

- Docker
- Paper (MC Server) .jar
- Velocity (MC Proxy) .jar
- MC World files (either use mine or generate your own)

Install Docker:
```sh
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Start

```sh
# Build images
docker compose build

# Start controller, proxy, and map (Paper starts on demand when a player connects)
docker compose up -d controller velocity squaremap

# Create the Paper container without starting it
docker compose create paper
```

### Accessing Consoles

```sh
# Velocity console
docker attach minecraft-velocity-1
# Detach: Ctrl+P then Ctrl+Q

# Paper console (only when running)
docker attach minecraft-paper-1
# Detach: Ctrl+P then Ctrl+Q

# View logs without attaching
docker compose logs -f velocity
docker compose logs -f paper
```

### Adding a Player

```sh
./add_player.sh <username>
```

This calls the controller which: looks up the Mojang UUID, runs `whitelist add` on Paper via docker exec (starting Paper first if needed), and grants the vane-velocity autostart permission on Velocity via docker exec.

### Backups

Backups run automatically via cron at 4am daily.

The script:
1. Sends `save-all` to Paper via the controller
2. Zips the three world directories to a temp file on the SSD
3. Copies the zip to local storage (HDD), keeping the last 10
4. Uploads the zip to Google Drive (`remote:minecraft-backups`), keeping the last 3

To run manually:
```sh
sudo ./backup.sh
```

### Other commands
You can directly interact with the controller endpoints by sending HTTP requests with curl.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Shows running status of Paper and Velocity containers |
| `/start` | POST | Starts the Paper container |
| `/stop` | POST | Stops the Paper container |
| `/save` | POST | Sends `save-all` to the Paper console |
| `/whitelist/<username>` | POST | Whitelists a player and grants autostart permission |

Examples:
```sh
curl http://localhost:5000/health
curl -X POST http://localhost:5000/start
curl -X POST http://localhost:5000/stop
curl -X POST http://localhost:5000/save
curl -X POST http://localhost:5000/whitelist/playername
```
---

## Restoring from Backup

Use this procedure to fully recreate the server from scratch.

### 1. Set up the host machine

Install Debian, Docker, and clone this repo:
```sh
sudo apt install git curl -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
git clone https://github.com/callisto-h/mc-server-files.git
cd mc-server-files
```

### 2. Populate secrets

Create `.env` and `velocity_proxy/forwarding.secret` as described in the Secrets section above. Make sure `paper_server/config/paper-global.yml` matches the forwarding secret. Check the Velocity Proxy setup page for more details.

### 3. Restore world files from Google Drive

Go to [Google Drive](https://drive.google.com/drive/folders/1q1wQFGsYtjz5pzV7XfvGVbW0ic2190LV?usp=drive_link). Download the most recent `snapshot_YYYY-MM-DD_HH-MM-SS.zip` file.

Extract the world folders into the paper_server directory:
```sh
unzip snapshot_*.zip -d paper_server/
```

Verify you have all three world folders:
```sh
ls paper_server/world paper_server/world_nether paper_server/world_the_end
```

### 4. Update the backup script (optional, for backups)

Update the following variables in `backup.sh` to match your system:

| Variable | Description |
|----------|-------------|
| `SRC` | Path to the paper_server directory containing the world folders |
| `TEMP_DIR` | Staging directory where the zip is created before upload |
| `LOCAL_DST` | Destination where zipped snapshots are stored |
| `DRIVE_DST` | Google Drive remote and folder name as configured in rclone |
| `KEEP_LOCAL` | Number of snapshots to retain on local before deleting the oldest |
| `KEEP_DRIVE` | Number of snapshots to retain on Google Drive — keep this low if on a free 15GB account |
| `LOG` | Path to the backup log file |
| `CONTROLLER_URL` | URL of the controller — only change this if running the controller on a non-standard port |

Install rclone to handle Google Drive uploads:
```sh
curl https://rclone.org/install.sh | sudo bash
rclone config
```

During `rclone config`, create a new remote of type `drive`, name it `remote` (or update `DRIVE_DST` to match whatever name you choose), and follow the OAuth flow to authenticate with your Google account. Once configured, test it with:
```sh
rclone lsd remote:
```

### 5. Retrieve missing .jar files

`.jar` files are Java executables — they are the server software itself and all of its plugins. They are not included in this repo due to their size, but all are freely available to download.

**Server and proxy jars** — download and place in the correct directory:

| Jar | Download | Destination |
|-----|----------|-------------|
| PaperMC | [papermc.io/downloads](https://papermc.io/downloads) | `paper_server/` |
| Velocity | [papermc.io/downloads/velocity](https://papermc.io/downloads/velocity) | `velocity_proxy/` |

Make sure to download the same versions that were previously running. The exact filenames are recorded in `paper_server/README.md` and `velocity_proxy/` directory listing.

**Plugin jars** — a list of all previously installed plugins is recorded in:
- `paper_server/plugins/jars.txt` — Paper plugins, download from [hangar.papermc.io](https://hangar.papermc.io)
- `velocity_proxy/plugins/jars.txt` — Velocity plugins, download from [hangar.papermc.io](https://hangar.papermc.io)

Place downloaded Paper plugin jars in `paper_server/plugins/` and Velocity plugin jars in `velocity_proxy/plugins/`.

### 6. Build and start

```sh
docker compose build
docker compose up -d controller velocity squaremap
docker compose create paper
```

### 7. Forward ports on your router

| Port | Service |
|------|---------|
| 25565 | Minecraft (Velocity) |
| 8080 | Squaremap live map |

### 8. Set up backup cron

```sh
sudo crontab -e
# Add: 0 4 * * * /path/to/backup.sh
```

### 9. Adjust memory allocation

The Paper container is configured to use between 4GB and 10GB of RAM. These values are set in `paper_server/start.sh`:
```sh
-Xms4G -Xmx10G
```

`-Xms` is the amount of memory reserved on startup, and `-Xmx` is the maximum it can grow to. Adjust these to match the available RAM on your host machine, keeping in mind that the OS, Docker, and the Velocity and controller containers also need headroom.

If you update these values you will need to rebuild the `paper` container with `docker compose build` and `docker compose create paper`.

---

## Network Layout

| Container | Internal address | External port |
|-----------|-----------------|---------------|
| velocity | velocity:25565 | 25565 |
| paper | paper:25575 | none |
| controller | controller:5000 | 5000 (host only) |
| squaremap | squaremap:80 | 8080 |

Paper is bound to the internal Docker network only and is never reachable from outside the host.
