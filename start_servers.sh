#!/bin/bash
# Start both the Flask web UI and FastAPI server
# Usage: ./start_servers.sh

echo "Starting Reddit Group Manager servers..."

# load .env when running outside Docker
set -a
. ./.env
set +a

# Default Redis URL for RQ if not set in the environment
RQ_REDIS_URL=${RQ_REDIS_URL:-redis://localhost:6379}


# Get Python version being used
PYTHON_BIN=$(which python)
echo "Using Python: $PYTHON_BIN"

# Make sure instance directory exists
mkdir -p instance

# Run database migrations once before starting services
echo "Running database migrations..."
python run_migrations.py || { echo "Migration step failed"; exit 1; }
# Export runtime configuration for the API
API_PORT=${API_PORT:-8015}
FRONTEND_PORT=${FRONTEND_PORT:-5015}
export API_PORT
export FRONTEND_PORT
export DATABASE_PATH="instance/app.db"

# Start Flask web UI and FastAPI server (run.py)
echo "Starting web UI and FastAPI via run.py on ports $FRONTEND_PORT and $API_PORT..."
$PYTHON_BIN run.py &
FLASK_PID=$!
echo "run.py started with PID: $FLASK_PID"

# Start RQ worker for "posts" and default queues
echo "Starting RQ worker for 'posts' and 'default' queues..."
$PYTHON_BIN worker.py posts default &
WORKER_PID=$!
echo "RQ worker started with PID: $WORKER_PID"

# Start the scheduler for periodic status checks
echo "Starting RQ scheduler on 'posts' queue..."
rqscheduler --url "$RQ_REDIS_URL" &
SCHED_PID=$!
echo "RQ scheduler started with PID: $SCHED_PID"

echo ""
echo "Processes are running!"
echo "- Web UI and API via run.py (PID $FLASK_PID)"
echo "- API docs: http://localhost:$API_PORT/docs"
echo "- RQ worker PID $WORKER_PID"
echo "- RQ scheduler PID $SCHED_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap Ctrl+C to kill all services
trap "kill $FLASK_PID $WORKER_PID $SCHED_PID; echo 'Services stopped'; exit" INT

# Wait for all processes
wait
