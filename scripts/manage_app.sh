#!/bin/bash
# Central script to manage the application lifecycle (API + Worker)

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function shutdown_apps() {
    log_info "Stopping API and Worker processes..."
    # Using SIGTERM for graceful shutdown
    pkill -f "uvicorn src.presentation.api.main:app" 2>/dev/null
    pkill -f "arq src.worker.WorkerSettings" 2>/dev/null
}

function shutdown_infra() {
    log_info "Stopping infrastructure containers..."
    docker stop arppool007 mailpit007 2>/dev/null
}

function stop_all() {
    echo ""
    shutdown_apps
    shutdown_infra
    log_success "Application stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap stop_all SIGINT SIGTERM

case "$1" in
    start)
        log_info "Starting Application (Redis + API + Worker)..."
        
        # 0. Ensure Redis is running
        if [ "$(docker ps -q -f name=arppool007)" ]; then
            log_success "Redis container 'arppool007' is already running."
        elif [ "$(docker ps -aq -f name=arppool007)" ]; then
            log_info "Starting existing Redis container 'arppool007'..."
            docker start arppool007 > /dev/null
        else
            log_info "Creating and starting new Redis container 'arppool007'..."
            docker run -d --name arppool007 -p 6379:6379 redis > /dev/null
        fi

        # 0b. Ensure Mailpit is running
        if [ "$(docker ps -q -f name=mailpit007)" ]; then
            log_success "Mailpit container 'mailpit007' is already running."
        elif [ "$(docker ps -aq -f name=mailpit007)" ]; then
            log_info "Starting existing Mailpit container 'mailpit007'..."
            docker start mailpit007 > /dev/null
        else
            log_info "Creating and starting new Mailpit container 'mailpit007'..."
            docker run -d --name mailpit007 -p 1025:1025 -p 8025:8025 axllent/mailpit > /dev/null
        fi

        # 1. Start API in background
        log_info "Starting FastAPI server on http://localhost:8000"
        uv run uvicorn src.presentation.api.main:app --reload --port 8000 &
        API_PID=$!

        # 2. Start Worker in background
        log_info "Starting ARQ Worker..."
        uv run arq src.worker.WorkerSettings &
        WORKER_PID=$!

        log_success "System is up! Press Ctrl+C to shut down."
        
        # Wait for processes
        wait
        ;;
    
    stop)
        stop_all
        ;;

    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
