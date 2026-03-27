#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/infrastructure/scripts/03-myragdb-manage.sh
# Description: MyRAGDB management script for infrastructure orchestration
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-01-05

source "$(dirname "$0")/_shared.sh"

COMMAND="${1:-status}"

case "$COMMAND" in
    start)
        print_header "Starting MyRAGDB"

        if [ ! -d "$MYRAGDB_PATH" ]; then
            print_error "MyRAGDB path not found: $MYRAGDB_PATH"
            exit 1
        fi

        if myragdb_is_running; then
            pid=$(myragdb_get_pid)
            print_success "MyRAGDB already running (PID: $pid)"
            exit 0
        fi

        cd "$MYRAGDB_PATH" || exit 1

        # Check if start.sh exists
        if [ ! -f "start.sh" ]; then
            print_error "start.sh not found in $MYRAGDB_PATH"
            exit 1
        fi

        print_info "Starting MyRAGDB in background (database loading may take several minutes)..."

        # Run start.sh in background to avoid blocking
        "./start.sh" >/tmp/myragdb_startup.log 2>&1 &
        STARTUP_PID=$!

        print_success "MyRAGDB startup initiated (background PID: $STARTUP_PID)"
        print_info "Database loading can take several minutes depending on repository size"
        print_info "Health checks will verify readiness with configurable timeouts"

        exit 0
        ;;

    stop)
        print_header "Stopping MyRAGDB"

        if [ ! -d "$MYRAGDB_PATH" ]; then
            print_error "MyRAGDB path not found: $MYRAGDB_PATH"
            exit 1
        fi

        cd "$MYRAGDB_PATH" || exit 1

        if ! myragdb_is_running; then
            print_success "MyRAGDB is not running"
            exit 0
        fi

        # Check if stop.sh exists
        if [ ! -f "stop.sh" ]; then
            print_error "stop.sh not found in $MYRAGDB_PATH"
            exit 1
        fi

        print_info "Stopping MyRAGDB..."
        if "./stop.sh" >/dev/null 2>&1; then
            print_success "MyRAGDB stopped successfully"
            exit 0
        else
            print_error "Failed to stop MyRAGDB via stop.sh"
            exit 1
        fi
        ;;

    status)
        print_header "MyRAGDB Status"

        if [ ! -d "$MYRAGDB_PATH" ]; then
            print_error "MyRAGDB path not found: $MYRAGDB_PATH"
            exit 1
        fi

        if myragdb_is_running; then
            pid=$(myragdb_get_pid)
            print_success "MyRAGDB is running (PID: $pid)"

            # Attempt health check
            if curl -s --max-time 2 "$MYRAGDB_HEALTH_ENDPOINT" >/dev/null 2>&1; then
                print_success "MyRAGDB health check passed"
            else
                print_warning "MyRAGDB is running but health endpoint not responding"
            fi

            exit 0
        else
            print_error "MyRAGDB is not running"
            exit 1
        fi
        ;;

    health)
        # Health check command for monitoring integration
        if wait_for_health "$MYRAGDB_HEALTH_ENDPOINT" "MyRAGDB" "$HEALTH_TIMEOUT_MS" "$HEALTH_RETRY_COUNT" "$HEALTH_RETRY_INTERVAL"; then
            exit 0
        else
            exit 1
        fi
        ;;

    *)
        echo "Usage: $0 <start|stop|status|health>"
        exit 1
        ;;
esac
