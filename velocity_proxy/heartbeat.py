#!/usr/bin/env python3
import os
import socket
import struct
import json
import time
import logging
import requests

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuration (from environment) ──────────────────────────────────────────
FLY_URL        = os.environ["FLY_URL"]
HEARTBEAT_KEY  = os.environ["HEARTBEAT_KEY"]
MC_HOST        = "paper"       # Docker service name
MC_PORT        = 25565
CHECK_INTERVAL = 60
# ───────────────────────────────────────────────────────────────────────────────


def get_player_count(host: str, port: int) -> int:
    """Returns player count, or 0 if server is unreachable."""
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            def pack_varint(val):
                data = b""
                while True:
                    part = val & 0x7F
                    val >>= 7
                    if val:
                        part |= 0x80
                    data += bytes([part])
                    if not val:
                        break
                return data

            host_bytes = host.encode("utf-8")
            handshake  = (
                pack_varint(0x00)
                + pack_varint(763)
                + pack_varint(len(host_bytes))
                + host_bytes
                + struct.pack(">H", port)
                + pack_varint(1)
            )
            s.sendall(pack_varint(len(handshake)) + handshake)
            s.sendall(b"\x01\x00")

            def read_varint(sock):
                result, shift = 0, 0
                while True:
                    b = sock.recv(1)
                    if not b:
                        return 0
                    val = b[0]
                    result |= (val & 0x7F) << shift
                    if not (val & 0x80):
                        return result
                    shift += 7

            length = read_varint(s)
            data   = b""
            while len(data) < length:
                chunk = s.recv(length - len(data))
                if not chunk:
                    break
                data += chunk

            idx = 0
            while data[idx] & 0x80:
                idx += 1
            idx += 1
            while data[idx] & 0x80:
                idx += 1
            idx += 1

            payload = json.loads(data[idx:].decode("utf-8"))
            players = payload.get("players", {}).get("online", 0)
            log.debug(f"Paper online, players={players}")
            return players

    except Exception as e:
        log.debug(f"Paper unreachable: {e}")
        return 0


def send_heartbeat(players: int):
    log.debug(f"Sending heartbeat — players={players}")
    try:
        resp = requests.post(FLY_URL, json={
            "key":     HEARTBEAT_KEY,
            "online":  True,      # proxy is running = online
            "players": players,
        }, timeout=10)
        if resp.status_code == 200:
            log.info(f"Heartbeat OK — players={players}")
        elif resp.status_code == 401:
            log.error("Heartbeat rejected — HEARTBEAT_KEY mismatch")
        else:
            log.warning(f"Heartbeat unexpected: {resp.status_code} {resp.text}")
    except requests.exceptions.ConnectionError as e:
        log.error(f"Heartbeat connection failed: {e}")
    except requests.exceptions.Timeout:
        log.error("Heartbeat timed out")
    except Exception as e:
        log.error(f"Heartbeat failed: {e}")


if __name__ == "__main__":
    log.info(f"Heartbeat started — checking paper:{MC_PORT} every {CHECK_INTERVAL}s")
    while True:
        players = get_player_count(MC_HOST, MC_PORT)
        send_heartbeat(players)
        time.sleep(CHECK_INTERVAL)
