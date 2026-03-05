#!/bin/sh
cd /server

# Start heartbeat in background
python3 heartbeat.py > logs/heartbeat.log 2>&1 &
HEARTBEAT_PID=$!
echo "Heartbeat started (PID $HEARTBEAT_PID)"

# Start Velocity
java -Xms128M -Xmx256M -XX:+UseG1GC -XX:G1HeapRegionSize=4M \
  -XX:+UnlockExperimentalVMOptions -XX:+ParallelRefProcEnabled \
  -XX:+AlwaysPreTouch -XX:MaxInlineLevel=15 \
  -jar velocity*.jar

# Velocity has exited — kill heartbeat
echo "Stopping heartbeat..."
kill $HEARTBEAT_PID
