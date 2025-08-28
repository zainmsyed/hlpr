#!/bin/bash
# Initial setup script for hlpr development environment

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

# Check if uv is installed
check_uv() {
    if ! command -v uv >/dev/null 2>&1; then
        log_error "uv is not installed. Please install it first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment with uv..."
    uv sync
    log_success "Python environment ready!"
}

# Setup Docker environment
setup_docker() {
    log_info "Setting up Docker environment..."

    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_info "Creating .env file template..."
        cat > .env << 'EOF'
# OpenAI API Key (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Gemini API Key (optional)
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
HLPR_DATABASE_URL=sqlite+aiosqlite:///./hlpr.db
HLPR_SQL_ECHO=false

# Application Settings
HLPR_ENVIRONMENT=dev
HLPR_DEBUG=true
EOF
        log_warning "Please edit .env file and add your API keys if needed"
    fi

    # Build and start Docker services
    log_info "Building Docker images..."
    docker compose build

    log_info "Starting Docker services..."
    docker compose up -d

    log_info "Waiting for database to be ready..."
    sleep 10

    log_success "Docker environment ready!"
}

# Initialize database
init_database() {
    log_info "Initializing database..."
    ./scripts/docker-exec.sh uv run hlpr db-init
    log_success "Database initialized!"
}

# Run basic health check
health_check() {
    log_info "Running health check..."
    ./scripts/docker-exec.sh uv run hlpr health
    log_success "Health check passed!"
}

# Main setup function
main() {
    log_info "Starting hlpr development environment setup..."

    # Pre-flight checks
    check_uv
    check_docker

    # Setup components
    setup_python
    setup_docker
    init_database
    health_check

    # Final instructions
    log_success "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "  1. Edit .env file to add API keys if needed"
    echo "  2. Use './scripts/dev.sh start' to start the environment"
    echo "  3. Use './scripts/dev.sh shell' to access the container"
    echo "  4. Visit http://localhost:8000 for the web interface"
    echo "  5. Run './scripts/dev.sh help' for more commands"
    echo
    log_info "Happy coding! 🚀"
}

# Run main setup
main