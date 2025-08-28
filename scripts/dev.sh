#!/bin/bash
# Development helper script for hlpr project

set -e

PROJECT_NAME="hlpr"

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

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Check if docker-compose exists
check_compose() {
    if ! command -v docker compose >/dev/null 2>&1; then
        log_error "docker compose command not found. Please install Docker Compose."
        exit 1
    fi
}

# Main functions
start() {
    log_info "Starting ${PROJECT_NAME} development environment..."
    check_docker
    check_compose
    docker compose up -d
    log_success "Development environment started!"
    log_info "Application will be available at http://localhost:8000"
    log_info "Run '$0 logs' to see logs or '$0 shell' to access the container"
}

stop() {
    log_info "Stopping ${PROJECT_NAME} development environment..."
    check_compose
    docker compose down
    log_success "Development environment stopped!"
}

restart() {
    log_info "Restarting ${PROJECT_NAME} development environment..."
    stop
    start
}

shell() {
    log_info "Opening shell in ${PROJECT_NAME} app container..."
    check_docker
    check_compose
    docker compose exec app bash
}

logs() {
    log_info "Showing logs for ${PROJECT_NAME} services..."
    check_compose
    if [ $# -eq 0 ]; then
        docker compose logs -f
    else
        docker compose logs -f "$1"
    fi
}

clean() {
    log_warning "This will remove all containers, volumes, and images for ${PROJECT_NAME}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up ${PROJECT_NAME} development environment..."
        check_compose
        docker compose down -v --rmi all
        docker system prune -f
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

build() {
    log_info "Building ${PROJECT_NAME} Docker images..."
    check_docker
    check_compose
    docker compose build --no-cache
    log_success "Build completed!"
}

status() {
    log_info "Checking status of ${PROJECT_NAME} services..."
    check_compose
    docker compose ps
}

# Help function
help() {
    echo "Development helper script for ${PROJECT_NAME}"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Start the development environment"
    echo "  stop      Stop the development environment"
    echo "  restart   Restart the development environment"
    echo "  shell     Open a shell in the app container"
    echo "  logs      Show logs (optionally specify service name)"
    echo "  clean     Remove all containers, volumes, and images"
    echo "  build     Build Docker images"
    echo "  status    Show status of services"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start          # Start development environment"
    echo "  $0 logs app       # Show logs for app service only"
    echo "  $0 shell          # Access app container shell"
}

# Main script logic
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    shell)
        shell
        ;;
    logs)
        shift
        logs "$@"
        ;;
    clean)
        clean
        ;;
    build)
        build
        ;;
    status)
        status
        ;;
    help|*)
        help
        ;;
esac