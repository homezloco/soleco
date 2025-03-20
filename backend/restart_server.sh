#!/bin/bash

# Kill any existing process on port 8001
pid=$(lsof -ti:8001)
if [ ! -z "$pid" ]; then
    echo "Killing existing process on port 8001 (PID: $pid)"
    kill -9 $pid
fi

# Start the server
echo "Starting server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 --reload