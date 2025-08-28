#!/bin/bash
# Smart Docker command execution wrapper for hlpr

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect execution context
detect_context() {
    # Check if we're already inside a Docker container
    if [ -f /.dockerenv ]; then
        echo "docker_inside"
        return
    fi

    # Check if Docker Compose services are running
    if docker compose ps --quiet 2>/dev/null | grep -q .; then
        echo "docker_available"
        return
    fi

    # Check if Docker daemon is available
    if docker info >/dev/null 2>&1; then
        echo "docker_available"
        return
    fi

    echo "local_only"
}

# Execute command based on context
execute_command() {
    local context="$1"
    shift
    local cmd="$*"

    case "$context" in
        docker_inside)
            log_info "Running inside Docker container, executing directly..."
            exec $cmd
            ;;
        docker_available)
            log_info "Docker available, routing through docker compose..."
            # Check if services are running
            if ! docker compose ps --quiet 2>/dev/null | grep -q .; then
                log_warning "Docker services not running. Starting them..."
                docker compose up -d
                sleep 2
            fi
            docker compose exec -T app $cmd
            ;;
        local_only)
            log_info "No Docker available, running locally..."
            exec $cmd
            ;;
        *)
            log_error "Unknown execution context: $context"
            exit 1
            ;;
    esac
}

# Main script
main() {
    if [ $# -eq 0 ]; then
        log_error "No command provided"
        echo "Usage: $0 <command> [args...]"
        echo "Example: $0 uv run hlpr health"
        exit 1
    fi

    local context
    context=$(detect_context)
    log_info "Detected execution context: $context"

    execute_command "$context" "$@"
}

# Run main function with all arguments
main "$@"