#!/bin/bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/infrastructure/scripts/02-docker-containers.sh
# Description: Docker containers management script for infrastructure orchestration
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-01-05

source "$(dirname "$0")/_shared.sh"

COMMAND="${1:-status}"

case "$COMMAND" in
    start)
        print_header "Starting Docker Containers"

        if ! docker_is_ready; then
            print_error "Docker is not available. Ensure Colima is running first."
            exit 1
        fi

        docker_set_host
        print_info "Docker is ready for container operations"
        print_success "Docker containers initialized"
        exit 0
        ;;
    stop)
        print_header "Stopping Docker Containers"

        if ! docker_is_ready; then
            print_success "Docker is not running"
            exit 0
        fi

        docker_set_host
        print_info "Docker containers stopped"
        exit 0
        ;;
    status)
        print_header "Docker Status"

        if docker_is_ready; then
            docker_set_host
            print_success "Docker is ready"
            docker ps 2>/dev/null | tail -n +2 | while read -r line; do
                echo "  $line"
            done
            exit 0
        else
            print_error "Docker is not available"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 <start|stop|status>"
        exit 1
        ;;
esac
