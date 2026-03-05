#!/bin/sh
if [ -z "$1" ]; then
    echo "Usage: $0 <username>"
    exit 1
fi

curl -s -X POST http://localhost:5000/whitelist/$1 | python3 -m json.tool
