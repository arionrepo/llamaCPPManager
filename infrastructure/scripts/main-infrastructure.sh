#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/infrastructure/scripts/main-infrastructure.sh
# Description: Main orchestrator for infrastructure services (Colima, Docker, MyRAGDB)
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-01-05

source "$(dirname "$0")/_shared.sh"

# Parse command-line arguments
COMMAND="${1:-status}"
SERVICE="${2:-}"
SKIP_COLIMA=false
SKIP_DOCKER=false
SKIP_MYRAGDB=false

# Helper function to show usage
show_usage() {
    cat << 'EOF'
Usage: main-infrastructure.sh <command> [options]

Commands:
  start              Start all infrastructure services
  stop               Stop all infrastructure services
  status             Show status of all services
  restart SERVICE    Restart a specific service (colima|docker|myragdb)

Options:
  --skip-colima      Skip Colima in start/stop operations
  --skip-docker      Skip Docker in start/stop operations
  --skip-myragdb     Skip MyRAGDB in start/stop operations

Examples:
  main-infrastructure.sh start                    # Start all services
  main-infrastructure.sh start --skip-colima      # Start Docker & MyRAGDB only
  main-infrastructure.sh stop                     # Stop all services
  main-infrastructure.sh status                   # Show all status
  main-infrastructure.sh restart myragdb          # Restart MyRAGDB
EOF
}

# Parse skip flags
parse_flags() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --skip-colima)
                SKIP_COLIMA=true
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                ;;
            --skip-myragdb)
                SKIP_MYRAGDB=true
                ;;
            *)
                ;;
        esac
        shift
    done
}

# Parse all remaining arguments for flags
shift
parse_flags "$@"

case "$COMMAND" in
    start)
        print_header "Infrastructure Startup"

        local failed=0

        # Start Colima
        if [ "$SKIP_COLIMA" = false ]; then
            print_info "Starting Colima..."
            if "$SCRIPT_DIR/01-colima-manage.sh" start; then
                sleep 2
            else
                print_error "Colima startup failed"
                failed=$((failed + 1))
            fi
        else
            print_info "Skipping Colima (--skip-colima)"
        fi

        # Start Docker
        if [ "$SKIP_DOCKER" = false ]; then
            print_info "Initializing Docker..."
            if "$SCRIPT_DIR/02-docker-containers.sh" start; then
                sleep 1
            else
                print_warning "Docker initialization failed (may require Colima)"
                # Don't fail completely, Docker failure is non-critical
            fi
        else
            print_info "Skipping Docker (--skip-docker)"
        fi

        # Start MyRAGDB
        if [ "$SKIP_MYRAGDB" = false ]; then
            print_info "Starting MyRAGDB..."
            if "$SCRIPT_DIR/03-myragdb-manage.sh" start; then
                true
            else
                print_error "MyRAGDB startup failed"
                failed=$((failed + 1))
            fi
        else
            print_info "Skipping MyRAGDB (--skip-myragdb)"
        fi

        echo ""
        if [ $failed -eq 0 ]; then
            print_success "Infrastructure startup completed successfully"
            exit 0
        else
            print_error "Infrastructure startup completed with $failed error(s)"
            exit 1
        fi
        ;;

    stop)
        print_header "Infrastructure Shutdown"

        local failed=0

        # Stop MyRAGDB
        if [ "$SKIP_MYRAGDB" = false ]; then
            print_info "Stopping MyRAGDB..."
            if "$SCRIPT_DIR/03-myragdb-manage.sh" stop; then
                sleep 1
            else
                print_warning "MyRAGDB stop failed or was not running"
            fi
        fi

        # Stop Docker (no-op mostly)
        if [ "$SKIP_DOCKER" = false ]; then
            print_info "Stopping Docker..."
            "$SCRIPT_DIR/02-docker-containers.sh" stop >/dev/null 2>&1 || true
            sleep 1
        fi

        # Stop Colima
        if [ "$SKIP_COLIMA" = false ]; then
            print_info "Stopping Colima..."
            if "$SCRIPT_DIR/01-colima-manage.sh" stop; then
                true
            else
                print_warning "Colima stop failed or was not running"
            fi
        fi

        echo ""
        print_success "Infrastructure shutdown completed"
        exit 0
        ;;

    status)
        print_header "Infrastructure Status"
        echo ""

        # Colima status
        if "$SCRIPT_DIR/01-colima-manage.sh" status 2>&1; then
            true
        fi
        echo ""

        # Docker status
        if "$SCRIPT_DIR/02-docker-containers.sh" status 2>&1; then
            true
        fi
        echo ""

        # MyRAGDB status
        if "$SCRIPT_DIR/03-myragdb-manage.sh" status 2>&1; then
            true
        fi
        echo ""

        exit 0
        ;;

    restart)
        if [ -z "$SERVICE" ]; then
            print_error "restart requires a service name (colima|docker|myragdb)"
            show_usage
            exit 1
        fi

        print_header "Restarting $SERVICE"

        case "$SERVICE" in
            colima)
                "$SCRIPT_DIR/01-colima-manage.sh" stop
                sleep 2
                "$SCRIPT_DIR/01-colima-manage.sh" start
                exit $?
                ;;
            docker)
                "$SCRIPT_DIR/02-docker-containers.sh" stop
                sleep 1
                "$SCRIPT_DIR/02-docker-containers.sh" start
                exit $?
                ;;
            myragdb)
                "$SCRIPT_DIR/03-myragdb-manage.sh" stop
                sleep 2
                "$SCRIPT_DIR/03-myragdb-manage.sh" start
                exit $?
                ;;
            *)
                print_error "Unknown service: $SERVICE"
                echo "Valid services: colima, docker, myragdb"
                exit 1
                ;;
        esac
        ;;

    help)
        show_usage
        exit 0
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
