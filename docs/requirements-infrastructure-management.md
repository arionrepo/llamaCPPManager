# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/requirements-infrastructure-management.md
# Description: Requirements for managing cloudflared tunnel and LLM controller infrastructure components
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-01

# Infrastructure Management Requirements

## 1. Purpose
Extend llamaCPPManager to manage critical infrastructure components (cloudflared tunnel and LLM controller) alongside LLM models, providing unified monitoring, health checking, process supervision, and automatic recovery for the complete local AI infrastructure stack.

## 2. Background
The current llamaCPPManager successfully manages llama.cpp model processes but lacks visibility and control over two essential infrastructure components:
1. **Cloudflared Tunnel**: Provides secure external access to local LLM services
2. **LLM Controller**: Orchestrates and routes requests across multiple LLM instances

Without managing these components, the system has blind spots and requires manual intervention when infrastructure fails.

## 3. Scope
This enhancement adds infrastructure component management to llamaCPPManager, enabling:
- Configuration tracking for cloudflared tunnel and LLM controller
- Unified start/stop/restart operations for all infrastructure components
- Health monitoring with configurable check intervals
- Automatic restart on failure with configurable retry policies
- Centralized logging for all components
- System startup integration (launchd agents)
- GUI visibility for infrastructure status

## 4. Granular Requirements

### Requirement 17: Infrastructure Configuration Management
**Phase**: MVP-Infrastructure
**User Story**: As a local operator, I want to configure cloudflared tunnel and LLM controller settings so that the system knows how to start and monitor these essential infrastructure components.

**Acceptance Criteria**:
- WHEN I run `llamacpp-manager init` THEN the system SHALL create default infrastructure configuration entries for cloudflared and controller
- WHEN I run `llamacpp-manager infra add cloudflared` THEN the system SHALL validate the cloudflared binary path and config file location
- WHEN I run `llamacpp-manager infra add controller` THEN the system SHALL validate the controller executable path and config file location
- WHEN I configure an infrastructure component THEN the system SHALL persist settings including: component name, binary path, config file path, working directory, environment variables, health check endpoint (if applicable), and autostart flag
- WHEN I list infrastructure components THEN the system SHALL display all configured components with their key settings
- WHEN I update or remove an infrastructure component THEN the system SHALL validate changes and update config atomically

**Configuration Schema**:
```yaml
infrastructure:
  cloudflared:
    enabled: true
    binary_path: /opt/homebrew/bin/cloudflared
    config_path: ~/.cloudflared/config.yml
    working_dir: ~/.cloudflared
    args: ["tunnel", "run", "llamacpp-tunnel"]
    env: {}
    autostart: true
    health_check:
      type: process  # or http
      interval_seconds: 30
    restart_policy:
      enabled: true
      max_retries: 3
      backoff_seconds: 10

  llm_controller:
    enabled: true
    binary_path: ~/llms/bin/llm-controller
    config_path: ~/llms/config/controller.yml
    working_dir: ~/llms
    args: ["--config", "controller.yml"]
    env:
      PORT: "8080"
    autostart: true
    health_check:
      type: http
      endpoint: "http://localhost:8080/health"
      interval_seconds: 30
      timeout_ms: 5000
    restart_policy:
      enabled: true
      max_retries: 3
      backoff_seconds: 10
```

---

### Requirement 18: Infrastructure Process Control
**Phase**: MVP-Infrastructure
**User Story**: As a local operator, I want to start, stop, and restart infrastructure components using the same interface as LLM models so that I have unified control over the entire system.

**Acceptance Criteria**:
- WHEN I run `llamacpp-manager infra start cloudflared` THEN the system SHALL spawn the cloudflared process with configured args and environment
- WHEN I run `llamacpp-manager infra start controller` THEN the system SHALL spawn the LLM controller process
- WHEN I run `llamacpp-manager infra start all` THEN the system SHALL start all enabled infrastructure components in dependency order (cloudflared before controller)
- WHEN an infrastructure component starts THEN the system SHALL write stdout/stderr to dedicated log files in the log directory
- WHEN an infrastructure component starts THEN the system SHALL write a PID file for process tracking
- WHEN I run `llamacpp-manager infra stop cloudflared` THEN the system SHALL send SIGTERM and gracefully shutdown the process
- WHEN graceful shutdown fails THEN the system SHALL send SIGKILL after a configurable timeout
- WHEN I run `llamacpp-manager infra restart <component>` THEN the system SHALL stop and start the component with appropriate delays
- WHEN I request a dry run THEN the system SHALL print the launch command without executing it

**Implementation Notes**:
- Reuse existing process management code from `process.py`
- Add infrastructure-specific PID tracking under `pids/infra/`
- Add infrastructure-specific logs under `logs/infra/`

---

### Requirement 19: Infrastructure Health Monitoring
**Phase**: MVP-Infrastructure
**User Story**: As an operator, I want continuous health monitoring of infrastructure components so that I can quickly detect failures and the system can automatically recover.

**Acceptance Criteria**:
- WHEN health checking is enabled THEN the system SHALL check each infrastructure component at configured intervals
- WHEN checking cloudflared THEN the system SHALL verify the process is running and optionally check tunnel connectivity
- WHEN checking the LLM controller THEN the system SHALL make HTTP health check requests to configured endpoints
- WHEN a health check succeeds THEN the system SHALL record success timestamp and clear failure counters
- WHEN a health check fails THEN the system SHALL increment failure counter and log the failure
- WHEN failures exceed threshold THEN the system SHALL trigger automatic restart if restart policy is enabled
- WHEN `llamacpp-manager status` runs THEN the system SHALL include infrastructure component status alongside model status
- WHEN `llamacpp-manager status --json` runs THEN the system SHALL include infrastructure component details in JSON output

**Health Check Types**:
1. **Process Check**: Verify PID exists and process is responsive
2. **HTTP Check**: Make HTTP GET request to health endpoint and verify response
3. **TCP Check**: Verify TCP port is accepting connections

**Status Output**:
```
Infrastructure Components:
  cloudflared        [RUNNING] pid=12345 uptime=2h15m health=ok
  llm_controller     [RUNNING] pid=12346 uptime=2h14m health=ok latency=15ms

LLM Models:
  smollm3           [RUNNING] pid=12350 port=8081 health=ok latency=23ms
  ...
```

---

### Requirement 20: Automatic Restart and Recovery
**Phase**: MVP-Infrastructure
**User Story**: As a reliability-focused operator, I want infrastructure components to automatically restart on failure so that the system self-heals without manual intervention.

**Acceptance Criteria**:
- WHEN a health check fails repeatedly THEN the system SHALL attempt automatic restart according to restart policy
- WHEN restarting a component THEN the system SHALL respect max_retries configuration
- WHEN restart attempts are exhausted THEN the system SHALL mark the component as FAILED and alert the operator
- WHEN backoff is configured THEN the system SHALL wait progressively longer between restart attempts
- WHEN a component restarts successfully THEN the system SHALL reset failure counters and log recovery
- WHEN I run `llamacpp-manager infra ensure-running` THEN the system SHALL check all infrastructure components and restart any that are down
- WHEN launchd mode is used THEN the system SHALL configure launchd KeepAlive and automatic restart behavior

**Restart Policy Configuration**:
```yaml
restart_policy:
  enabled: true
  max_retries: 3            # Maximum consecutive restart attempts
  backoff_seconds: 10       # Initial backoff between restarts
  backoff_multiplier: 2.0   # Exponential backoff multiplier
  health_check_failures: 3  # Failures before triggering restart
```

**Implementation Notes**:
- Add monitoring daemon or use existing status watch functionality
- Integrate with launchd for system-level supervision
- Log all restart attempts and outcomes

---

### Requirement 21: Configuration File Tracking and Validation
**Phase**: MVP-Infrastructure
**User Story**: As an operator managing complex configurations, I want the system to track where infrastructure config files are located and validate they exist so that I can troubleshoot configuration issues quickly.

**Acceptance Criteria**:
- WHEN I configure an infrastructure component THEN the system SHALL validate that config files exist at specified paths
- WHEN I run `llamacpp-manager infra config validate` THEN the system SHALL check all config file paths and report missing or invalid files
- WHEN I run `llamacpp-manager infra config show cloudflared` THEN the system SHALL display the current cloudflared configuration file location and optionally preview contents
- WHEN I run `llamacpp-manager infra config edit cloudflared` THEN the system SHALL open the cloudflared config file in the system default editor
- WHEN config files are moved or renamed THEN the system SHALL detect this during validation and provide clear error messages
- WHEN I migrate directories THEN the system SHALL support updating infrastructure config file paths

**Example Commands**:
```bash
llamacpp-manager infra config validate
llamacpp-manager infra config show cloudflared
llamacpp-manager infra config show controller
llamacpp-manager infra config edit cloudflared
llamacpp-manager infra config list --json
```

---

### Requirement 22: Unified Logging for Infrastructure
**Phase**: MVP-Infrastructure
**User Story**: As a troubleshooter, I want easy access to infrastructure component logs so that I can diagnose tunnel and controller issues quickly.

**Acceptance Criteria**:
- WHEN an infrastructure component starts THEN the system SHALL write stdout to `<log_dir>/infra/<component>.out.log`
- WHEN an infrastructure component starts THEN the system SHALL write stderr to `<log_dir>/infra/<component>.err.log`
- WHEN logs exceed size limits THEN the system SHALL rotate logs automatically
- WHEN I run `llamacpp-manager logs cloudflared` THEN the system SHALL display recent cloudflared logs
- WHEN I run `llamacpp-manager logs cloudflared --tail` THEN the system SHALL stream cloudflared logs in real-time
- WHEN I run `llamacpp-manager logs --all` THEN the system SHALL include both infrastructure and model logs
- WHEN I run `llamacpp-manager logs --json` THEN the system SHALL provide log file paths and recent entries in JSON format

**Log Organization**:
```
~/Library/Logs/llamaCPPManager/
  infra/
    cloudflared.out.log
    cloudflared.err.log
    llm_controller.out.log
    llm_controller.err.log
  models/
    smollm3.out.log
    smollm3.err.log
    ...
```

---

### Requirement 23: Launchd Integration for Infrastructure
**Phase**: MVP-Infrastructure
**User Story**: As a user who wants resilience, I want infrastructure components to run under launchd so that they autostart when my laptop boots and are supervised by macOS.

**Acceptance Criteria**:
- WHEN I run `llamacpp-manager launchd install cloudflared` THEN the system SHALL generate a valid plist for cloudflared in `~/Library/LaunchAgents`
- WHEN I run `llamacpp-manager launchd install controller` THEN the system SHALL generate a valid plist for the LLM controller
- WHEN I run `llamacpp-manager launchd install --all-infra` THEN the system SHALL install launchd agents for all enabled infrastructure components
- WHEN launchd agents are installed THEN the system SHALL configure KeepAlive for automatic restart
- WHEN launchd agents are installed THEN the system SHALL configure RunAtLoad for startup on boot
- WHEN I run `llamacpp-manager launchd uninstall cloudflared` THEN the system SHALL unload and remove the cloudflared agent
- WHEN I check status THEN the system SHALL distinguish between direct-mode and launchd-mode processes

**Example plist** (cloudflared):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.llamacpp.infra.cloudflared</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>llamacpp-tunnel</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/user/.cloudflared</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/user/Library/Logs/llamaCPPManager/infra/cloudflared.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/user/Library/Logs/llamaCPPManager/infra/cloudflared.err.log</string>
</dict>
</plist>
```

---

### Requirement 24: GUI Integration for Infrastructure
**Phase**: MVP-Infrastructure-GUI
**User Story**: As a macOS user, I want to see infrastructure component status in the menu bar GUI so that I have complete visibility into the system without opening a terminal.

**Acceptance Criteria**:
- WHEN I open the menu bar app THEN the system SHALL display an "Infrastructure" section showing cloudflared and controller status
- WHEN an infrastructure component is running THEN the system SHALL show a green indicator, PID, and uptime
- WHEN an infrastructure component is down THEN the system SHALL show a red indicator and "STOPPED" status
- WHEN an infrastructure component is starting THEN the system SHALL show a yellow indicator and "STARTING" status
- WHEN I click on an infrastructure component THEN the system SHALL show a submenu with Start/Stop/Restart/View Logs options
- WHEN I click "View Logs" THEN the system SHALL open the log file in Console.app or default viewer
- WHEN I click "Start" on a stopped component THEN the system SHALL invoke the CLI start command and refresh status
- WHEN health checks are failing THEN the system SHALL display a warning indicator and failure count

**GUI Layout**:
```
┌─────────────────────────────────┐
│ llamaCPP Manager                │
├─────────────────────────────────┤
│ Infrastructure                  │
│   ✓ Cloudflared   [Running]     │
│   ✓ Controller    [Running]     │
├─────────────────────────────────┤
│ Models                          │
│   ✓ smollm3       [Running]     │
│   ○ llama2        [Stopped]     │
├─────────────────────────────────┤
│ Start All Infrastructure        │
│ Stop All Infrastructure         │
│ Refresh Status                  │
│ Preferences...                  │
│ Quit                            │
└─────────────────────────────────┘
```

---

### Requirement 25: Startup and Boot Integration
**Phase**: MVP-Infrastructure
**User Story**: As a laptop user, I want the entire llamaCPPManager system (infrastructure + models) to start automatically when my laptop boots so that my AI infrastructure is always available.

**Acceptance Criteria**:
- WHEN I run `llamacpp-manager install-startup` THEN the system SHALL install launchd agents for all autostart-enabled components (both infrastructure and models)
- WHEN my laptop boots THEN the system SHALL start infrastructure components before starting model services
- WHEN I run `llamacpp-manager uninstall-startup` THEN the system SHALL remove all launchd agents
- WHEN I run `llamacpp-manager startup status` THEN the system SHALL show which components are configured for autostart
- WHEN the GUI app is configured to start at login THEN the system SHALL ensure the GUI launches after infrastructure is ready
- WHEN I configure startup order THEN the system SHALL support dependency ordering (cloudflared → controller → models)

**Implementation Options**:
1. **Launchd Agents**: Install individual agents with appropriate dependencies (preferred for macOS)
2. **GUI at Login**: macOS System Settings > Users & Groups > Login Items
3. **Master Launcher Script**: Single launchd agent that orchestrates startup sequence

---

### Requirement 26: Alerting and Notifications
**Phase**: MVP-Infrastructure
**User Story**: As an operator, I want to be notified when infrastructure components fail so that I can take action before users are affected.

**Acceptance Criteria**:
- WHEN an infrastructure component fails health checks repeatedly THEN the system SHALL log a CRITICAL alert
- WHEN automatic restart succeeds THEN the system SHALL log an INFO notification
- WHEN automatic restart fails after max retries THEN the system SHALL log an ERROR alert
- WHEN the GUI is running and a component fails THEN the system SHALL display a macOS notification
- WHEN I configure notification settings THEN the system SHALL support enabling/disabling notifications per component
- WHEN notifications are enabled THEN the system SHALL use macOS User Notifications framework

**Notification Examples**:
- "Cloudflared tunnel is down - attempting restart"
- "LLM Controller failed after 3 restart attempts - manual intervention required"
- "Infrastructure recovered: Cloudflared restarted successfully"

---

### Requirement 27: Infrastructure Metrics and Diagnostics
**Phase**: Future-Enhancement
**User Story**: As a system administrator, I want detailed metrics about infrastructure component performance so that I can optimize and troubleshoot the system.

**Acceptance Criteria** (Stretch Goals):
- WHEN I run `llamacpp-manager infra metrics` THEN the system SHALL display uptime, restart count, health check success rate, and latency stats
- WHEN I run `llamacpp-manager infra diagnose cloudflared` THEN the system SHALL run diagnostic checks (process status, config validation, connectivity tests)
- WHEN metrics collection is enabled THEN the system SHALL track historical health data
- WHEN I run `llamacpp-manager infra export-metrics` THEN the system SHALL export metrics in Prometheus format

---

## 5. Non-Functional Requirements

### Performance
- Infrastructure health checks SHALL complete within 5 seconds
- System startup (all infrastructure + models) SHALL complete within 30 seconds
- Health check monitoring SHALL use less than 1% CPU when idle
- Memory overhead for monitoring SHALL be less than 50MB

### Reliability
- Automatic restart SHALL have 95% success rate for transient failures
- Configuration validation SHALL prevent 100% of invalid startup attempts
- Launchd integration SHALL survive system reboots 100% of the time

### Usability
- All infrastructure commands SHALL follow the same patterns as model commands
- Error messages SHALL include specific remediation steps
- GUI status indicators SHALL update within 2 seconds of state changes

### Security
- Infrastructure component config files SHALL be readable only by owner (600 permissions)
- Log files SHALL not contain sensitive credentials or tokens
- Binary path validation SHALL prevent arbitrary code execution

---

## 6. Implementation Phases

### Phase 1: Core Infrastructure Management (MVP)
- Configuration schema and persistence
- Start/stop/restart commands for infrastructure
- Basic process tracking and PID management
- Log file management

### Phase 2: Health Monitoring and Recovery
- Health check framework
- Automatic restart policies
- Status reporting integration
- Alert logging

### Phase 3: Launchd and Startup Integration
- Launchd plist generation for infrastructure
- Boot startup automation
- Dependency ordering
- `install-startup` convenience commands

### Phase 4: GUI Integration
- Infrastructure status in menu bar
- Start/stop controls
- Health indicators and alerts
- Log viewer integration

### Phase 5: Advanced Features (Future)
- Metrics collection and export
- Diagnostic tools
- macOS User Notifications
- Prometheus endpoint

---

## 7. Dependencies and Prerequisites

### System Requirements
- macOS Ventura or newer (for launchd and notifications)
- cloudflared binary installed (`brew install cloudflared`)
- LLM controller binary (user-provided)
- Python 3.11+ (already required)

### Code Dependencies
- Reuse `process.py` for process management
- Extend `config.py` for infrastructure configuration
- Extend `health.py` for infrastructure health checks
- Extend `launchd.py` for infrastructure agent generation
- Extend GUI Swift code for infrastructure display

---

## 8. Success Metrics

### Measurable Goals
1. **Zero-Touch Operation**: System runs for 7 days without manual intervention
2. **Recovery Time**: Infrastructure recovers from failures within 60 seconds
3. **Visibility**: Operator can assess complete system health in under 5 seconds
4. **Reliability**: Infrastructure components maintain >99% uptime over 30 days

---

## 9. Open Questions

1. **Dependency Management**: Should cloudflared wait for network connectivity before starting? How do we handle startup ordering?
2. **Configuration Discovery**: Should the system auto-detect cloudflared config location, or require explicit configuration?
3. **Controller Protocol**: What is the specific health check endpoint and protocol for the LLM controller?
4. **Notification Preferences**: Should notifications be opt-in or opt-out? What severity levels trigger notifications?
5. **Log Retention**: What log rotation and retention policy should be applied to infrastructure logs?
6. **Testing Strategy**: How do we integration test infrastructure management without requiring actual cloudflared/controller binaries?

---

## 10. References and Related Documents

- [requirements.md](requirements.md) - Original llamaCPPManager requirements
- [design.md](design.md) - System architecture and design patterns
- [user-manual.md](user-manual.md) - End-user documentation
- Cloudflared documentation: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- macOS launchd documentation: `man launchd.plist`

---

**Document Status**: Draft for Review
**Next Steps**: Review with user, create design document, implement Phase 1

---

_Questions or feedback: libor@arionetworks.com_
