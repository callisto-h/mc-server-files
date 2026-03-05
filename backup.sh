#!/bin/sh

# ── Configuration ──────────────────────────────────────────────────────────────
SRC="/home/callisto/minecraft/mc-server-files/paper_server"
TEMP_DIR="/home/callisto/minecraft/temp"
LOCAL_DST="/mnt/backups/minecraft"
DRIVE_DST="remote:backups"
KEEP_LOCAL=10
KEEP_DRIVE=3
LOG="/home/callisto/minecraft/logs/backup.log"
CONTROLLER_URL="http://localhost:5000"
# ───────────────────────────────────────────────────────────────────────────────

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG"
}

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
ZIPFILE="snapshot_$TIMESTAMP.zip"
TEMP_ZIP="$TEMP_DIR/$ZIPFILE"

mkdir -p "$TEMP_DIR"
mkdir -p "$LOCAL_DST"
mkdir -p "$(dirname $LOG)"

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Starting backup — $TIMESTAMP"

# ── Save-all via controller ────────────────────────────────────────────────────
log "Sending save-all to Paper"
curl -s -X POST "$CONTROLLER_URL/save" >> "$LOG" 2>&1
sleep 3

# ── Zip world files to temp on SSD ────────────────────────────────────────────
log "Zipping world files to temp — $TEMP_ZIP"
zip -r "$TEMP_ZIP" \
    "$SRC/world" \
    "$SRC/world_nether" \
    "$SRC/world_the_end" \
    >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    log "ERROR: Zip failed"
    rm -f "$TEMP_ZIP"
    exit 1
fi
log "Zip complete — $(du -sh $TEMP_ZIP | cut -f1)"

# ── Copy zip to HDD ───────────────────────────────────────────────────────────
log "Copying to HDD — $LOCAL_DST/$ZIPFILE"
cp "$TEMP_ZIP" "$LOCAL_DST/$ZIPFILE"

if [ $? -ne 0 ]; then
    log "ERROR: HDD copy failed"
else
    log "HDD copy complete"
fi

# Prune old local backups
COUNT=$(ls -1 "$LOCAL_DST"/snapshot_*.zip 2>/dev/null | wc -l)
log "HDD: $COUNT backups (keeping $KEEP_LOCAL)"
if [ "$COUNT" -gt "$KEEP_LOCAL" ]; then
    DELETE=$((COUNT - KEEP_LOCAL))
    log "Removing $DELETE oldest HDD backup(s)"
    ls -1t "$LOCAL_DST"/snapshot_*.zip | tail -n "$DELETE" | while read f; do
        log "Deleting $f"
        rm -f "$f"
    done
fi

# ── Upload to Google Drive from temp ──────────────────────────────────────────
log "Uploading to Google Drive — $DRIVE_DST/$ZIPFILE"
rclone copy "$TEMP_ZIP" "$DRIVE_DST/" \
    --progress \
    --transfers 4 \
    --drive-chunk-size 128M \
    >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    log "ERROR: Google Drive upload failed"
else
    log "Google Drive upload complete"
fi

# Prune old Drive backups
log "Pruning old Drive backups (keeping $KEEP_DRIVE)"
DRIVE_BACKUPS=$(rclone ls "$DRIVE_DST" 2>/dev/null \
    | awk '{print $NF}' \
    | grep "^snapshot_.*\.zip$" \
    | sort)

DRIVE_COUNT=$(echo "$DRIVE_BACKUPS" | grep -c "snapshot_" 2>/dev/null || echo 0)
log "Drive: $DRIVE_COUNT backups"

if [ "$DRIVE_COUNT" -gt "$KEEP_DRIVE" ]; then
    DELETE=$((DRIVE_COUNT - KEEP_DRIVE))
    log "Removing $DELETE oldest Drive backup(s)"
    echo "$DRIVE_BACKUPS" | head -n "$DELETE" | while read f; do
        log "Deleting Drive: $f"
        rclone deletefile "$DRIVE_DST/$f" >> "$LOG" 2>&1
    done
fi

# ── Clean up temp ─────────────────────────────────────────────────────────────
log "Cleaning up temp"
rm -f "$TEMP_ZIP"

log "Backup complete"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
