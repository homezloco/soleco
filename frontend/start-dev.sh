#!/bin/bash

# Define the port
PORT=5181

# Check if the port is in use
pid=$(lsof -ti :$PORT)

# If the port is in use, kill the process
if [ ! -z "$pid" ]; then
  echo "Port $PORT is in use by process $pid. Killing process..."
  kill -9 $pid
  sleep 1
  echo "Process killed."
else
  echo "Port $PORT is free."
fi

# Start the development server
echo "Starting development server on port $PORT..."
npm run dev
