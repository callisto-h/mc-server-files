import os
import time
import socket
import logging
import requests
import docker
from flask import Flask, jsonify

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
PAPER_CONTAINER    = os.environ.get("PAPER_CONTAINER")
VELOCITY_CONTAINER = os.environ.get("VELOCITY_CONTAINER")
PAPER_HOST         = "paper"
PAPER_PORT         = 25575
STARTUP_TIMEOUT    = 60  # seconds to wait for Paper to be ready
# ───────────────────────────────────────────────────────────────────────────────

app           = Flask(__name__)
docker_client = docker.from_env()


def get_paper_container():
    try:
        return docker_client.containers.get(PAPER_CONTAINER)
    except docker.errors.NotFound:
        return None


def get_velocity_container():
    try:
        return docker_client.containers.get(VELOCITY_CONTAINER)
    except docker.errors.NotFound:
        return None

def paper_exec(command: str) -> str:
    """Send a command to the Paper console via stdin attach."""
    container = get_paper_container()
    if container is None or container.status != "running":
        log.warning(f"Paper not running, skipping command: {command}")
        return ""
    try:
        sock = container.attach_socket(params={"stdin": 1, "stream": 1})
        sock._sock.sendall((command + "\n").encode("utf-8"))
        sock.close()
        log.info(f"Paper stdin '{command}' sent")
        return "sent"
    except Exception as e:
        log.error(f"Paper stdin failed for '{command}': {e}")
        return ""

def velocity_exec(command: str) -> str:
    """Send a command to the Velocity console via stdin attach."""
    container = get_velocity_container()
    if container is None or container.status != "running":
        log.error("Velocity container not running, cannot exec command")
        return ""
    try:
        sock = container.attach_socket(params={"stdin": 1, "stream": 1})
        sock._sock.sendall((command + "\n").encode("utf-8"))
        sock.close()
        log.info(f"Velocity stdin '{command}' sent")
        return "sent"
    except Exception as e:
        log.error(f"Velocity stdin failed for '{command}': {e}")
        return ""

def wait_for_paper(timeout: int = STARTUP_TIMEOUT) -> bool:
    """Poll Paper's port until it accepts connections or timeout."""
    log.info(f"Waiting for Paper to be ready (timeout={timeout}s)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((PAPER_HOST, PAPER_PORT), timeout=2):
                log.info("Paper is ready")
                return True
        except OSError:
            log.debug("Paper not ready yet, retrying in 5s")
            time.sleep(5)
    log.error(f"Paper did not become ready within {timeout}s")
    return False


def ensure_paper_running() -> bool:
    """Start Paper if not running and wait for it to be ready."""
    container = get_paper_container()
    if container is None:
        log.error(f"Container '{PAPER_CONTAINER}' not found")
        return False

    if container.status != "running":
        log.info("Paper not running — starting it")
        container.start()

    return wait_for_paper()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/start", methods=["POST"])
def start():
    container = get_paper_container()
    if container is None:
        return jsonify({"error": f"Container '{PAPER_CONTAINER}' not found"}), 404

    status = container.status
    log.info(f"Start requested — container status: {status}")

    if status == "running":
        return jsonify({"ok": True, "message": "Already running"})

    container.start()
    log.info("Paper container started")
    return jsonify({"ok": True, "message": "Started"})


@app.route("/stop", methods=["POST"])
def stop():
    container = get_paper_container()
    if container is None:
        return jsonify({"error": f"Container '{PAPER_CONTAINER}' not found"}), 404

    status = container.status
    log.info(f"Stop requested — container status: {status}")

    if status != "running":
        return jsonify({"ok": True, "message": "Already stopped"})

    container.stop()
    log.info("Paper container stopped")
    return jsonify({"ok": True, "message": "Stopped"})


@app.route("/whitelist/<username>", methods=["POST"])
def whitelist(username: str):
    log.info(f"Whitelist request for '{username}'")

    # Look up UUID from Mojang API (needed for Velocity LuckPerms command)
    try:
        resp = requests.get(
            f"https://api.mojang.com/users/profiles/minecraft/{username}",
            timeout=10
        )
        if resp.status_code == 404:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        data = resp.json()
        raw_uuid = data["id"]
        name     = data["name"]
        uuid     = f"{raw_uuid[:8]}-{raw_uuid[8:12]}-{raw_uuid[12:16]}-{raw_uuid[16:20]}-{raw_uuid[20:]}"
        log.info(f"Resolved {name} → {uuid}")
    except Exception as e:
        log.error(f"Mojang API error: {e}")
        return jsonify({"error": "Failed to look up UUID"}), 500

    # Ensure Paper is running and ready
    log.info("Ensuring Paper is running for whitelist add")
    if not ensure_paper_running():
        return jsonify({"error": "Paper failed to start, cannot whitelist player"}), 500

    # Let Paper handle the whitelist — it uses the correct UUID format
    exec_results = {}
    exec_results["whitelist_add"] = paper_exec(f"whitelist add {name}")

    # Grant LuckPerms permission on Velocity
    exec_results["luckperms"] = velocity_exec(
        f"/lpv user {uuid} permission set vane_proxy.start_server.tng_survival true"
    )

    return jsonify({
        "ok":   True,
        "name": name,
        "uuid": uuid,
        "exec": exec_results,
    })


@app.route("/save", methods=["POST"])
def save():
    container = get_paper_container()
    if container is None or container.status != "running":
        return jsonify({"ok": True, "message": "Paper not running, skipping save"})
    result = paper_exec("save-all")
    return jsonify({"ok": True, "result": result})


@app.route("/health")
def health():
    paper    = get_paper_container()
    velocity = get_velocity_container()
    return jsonify({
        "ok":      True,
        "paper":    paper.status if paper else "not found",
        "velocity": velocity.status if velocity else "not found",
    })


if __name__ == "__main__":
    log.info("Controller starting")
    app.run(host="0.0.0.0", port=5000)
