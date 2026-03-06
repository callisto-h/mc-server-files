#!/bin/sh

if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Error: '$1' is not a directory"
    exit 1
fi

ls "$1"/*.jar 2>/dev/null | while read f; do
    basename "$f"
done > "$1/jars.txt"

echo "Written to $1/jars.txt"
