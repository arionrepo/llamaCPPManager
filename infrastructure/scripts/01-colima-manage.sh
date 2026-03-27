#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/infrastructure/scripts/01-colima-manage.sh
# Description: Colima management script for infrastructure orchestration
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-01-05

source "$(dirname "$0")/_shared.sh"

COMMAND="${1:-status}"

case "$COMMAND" in
    start)
        print_header "Starting Colima"
        colima_start
        exit $?
        ;;
    stop)
        print_header "Stopping Colima"
        colima_stop
        exit $?
        ;;
    status)
        print_header "Colima Status"
        if colima_is_running; then
            print_success "Colima is running"
            docker info 2>/dev/null | grep -E "^(Server Version|Containers|Images)" | sed 's/^/  /'
            exit 0
        else
            print_error "Colima is not running"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 <start|stop|status>"
        exit 1
        ;;
esac
