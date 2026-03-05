#!/bin/sh

# ── Configuration ──────────────────────────────────────────────────────────────
SRC="/home/callisto/minecraft/paper_server"           # Paper server directory
DST="/mnt/backups/minecraft"                   # HDD destination
KEEP=10                                        # Number of snapshots to keep
LOG="/var/log/mc_backup.log"
# ───────────────────────────────────────────────────────────────────────────────

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG"
}

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
SNAPSHOT="$DST/snapshot_$TIMESTAMP"

log "Starting backup — $SNAPSHOT"

mkdir -p "$DST"

# Flush world data to disk before copying
log "Sending save-all via controller"
curl -s -X POST http://localhost:5000/save && sleep 3
log "Proceeding with backup"

# Copy entire server directory as a timestamped snapshot
cp -r "$SRC" "$SNAPSHOT"

if [ $? -eq 0 ]; then
    log "Backup complete — $(du -sh $SNAPSHOT | cut -f1)"
else
    log "ERROR: Backup failed"
    exit 1
fi

# Count snapshots and remove oldest beyond KEEP limit
COUNT=$(ls -1d "$DST"/snapshot_* 2>/dev/null | wc -l)
log "HDD has $COUNT snapshots (keeping $KEEP)"

if [ "$COUNT" -gt "$KEEP" ]; then
    DELETE=$((COUNT - KEEP))
    log "Removing $DELETE oldest snapshot(s)"
    ls -1dt "$DST"/snapshot_* | tail -n "$DELETE" | while read f; do
        log "Deleting $f"
        rm -rf "$f"
    done
fi

log "Done"
