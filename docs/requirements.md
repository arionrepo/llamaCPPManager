# llamaCPPManager Requirements

## 1. Purpose
Create a lightweight macOS-friendly utility that helps operate multiple `llama-server` (llama.cpp) instances, exposing easy start/stop controls, health status, and quick access to logs/configs, with an optional native GUI.

## 2. Target Environments

### Local Development (macOS M4 Max)
- macOS (Apple Silicon, Ventura or newer)
- llama.cpp via Homebrew (`/opt/homebrew/bin/llama-server`) or user-specified path
- Models hosted locally under `~/llms/...`
- Docker/Colima for containerized deployments

### Remote Production (Ubuntu OpenStack)
- Kubernetes clusters on Ubuntu OpenStack
- Container registry for model images
- Persistent storage for model files
- Remote kubectl access from macOS CLI

## 3. Granular Requirements (Patterned)

Requirement 1: Configuration Management
Phase: MVP-CLI

User Story: As a local operator, I want to maintain a declarative list of models and runtime settings so that I can start and manage `llama-server` processes consistently without retyping flags.

Acceptance Criteria
- WHEN I run `llamacpp-manager init` THEN the system SHALL create default config and directories if missing
- WHEN I add a model via `config add` THEN the system SHALL validate paths and ports and persist to YAML
- WHEN I update or remove a model THEN the system SHALL validate the change and write an updated config atomically
- WHEN I list models via `config list` THEN the system SHALL display all entries including name, model_path, host, and port

Requirement 2: Direct Process Control
Phase: MVP-CLI

User Story: As a local operator, I want to start and stop models on demand so that I can run only what I need and free resources when done.

Acceptance Criteria
- WHEN I start a model via CLI THEN the system SHALL spawn `llama-server` with configured args and environment
- WHEN a model starts THEN the system SHALL write stdout/stderr to per-model log files
- WHEN I stop a model THEN the system SHALL send SIGTERM and, on timeout, SIGKILL
- WHEN I request a dry run THEN the system SHALL print the launch command without executing it

Requirement 3: Launchd Autostart Management
Phase: MVP-Autostart

User Story: As a user who wants resilience, I want models to run under launchd so that they autostart and are supervised by macOS.

Acceptance Criteria
- WHEN I install launchd for a model THEN the system SHALL generate a valid plist in `~/Library/LaunchAgents`
- WHEN I bootstrap the plist THEN the system SHALL load the agent and confirm active status
- WHEN I uninstall launchd for a model THEN the system SHALL unload and remove the plist
- WHEN `autostart` is true in config THEN the system SHALL reflect that in the generated agent

Requirement 4: Service Discovery & Status
Phase: MVP-Status

User Story: As an operator, I want to see which models are running and on which ports so that I can quickly assess system state.

Acceptance Criteria
- WHEN I run `status` THEN the system SHALL detect processes started directly or via launchd and show name, pid, host, and port
- WHEN a model is not running THEN the system SHALL display it as stopped
- WHEN `--watch` is used THEN the system SHALL refresh status at a regular interval without high CPU usage

Requirement 5: Health Check & Latency
Phase: MVP-Status

User Story: As an operator, I want to verify that each model endpoint responds and see basic latency so that I can gauge runtime health.

Acceptance Criteria
- WHEN `status` runs THEN the system SHALL attempt a fast HTTP check to `host:port`
- WHEN a model responds THEN the system SHALL record reachability and round-trip latency
- WHEN a model exposes version info THEN the system SHALL include it in the status output (if available)

Requirement 6: Logging & Tailing
Phase: MVP-Observability

User Story: As a troubleshooter, I want easy access to logs so that I can diagnose startup and runtime issues quickly.

Acceptance Criteria
- WHEN a model starts THEN the system SHALL write stdout/stderr to a rotating log in the configured log directory
- WHEN I run `logs <name> --tail` THEN the system SHALL stream the log for that model
- WHEN I request logs for all models THEN the system SHALL indicate log file locations and offer tail commands

Requirement 7: JSON Status for GUI
Phase: MVP-CLI

User Story: As a GUI developer, I want machine-readable status so that the menu bar app can render state without parsing human-formatted text.

Acceptance Criteria
- WHEN I run `status --json` THEN the system SHALL output a JSON array containing name, pid, host, port, up/down, latency_ms, version (if any), mode (direct|launchd), and log_path
- WHEN `config list --json` is called THEN the system SHALL output the current configuration as JSON

Requirement 8: Menu Bar GUI
Phase: MVP-GUI

User Story: As a macOS user, I want a simple menu bar app to start/stop models and view status so that I can manage models without a terminal.

Acceptance Criteria
- WHEN I open the menu THEN the system SHALL list configured models with up/down indicators, pid (if running), and latency
- WHEN I click Start/Stop/Restart on a model THEN the system SHALL invoke the corresponding CLI command and refresh status
- WHEN I open Preferences THEN the system SHALL allow updating paths and refresh interval and persist changes

Requirement 9: Packaging & Installation
Phase: Release-Prep

User Story: As a user, I want straightforward installation so that I can get started quickly without complex setup.

Acceptance Criteria
- WHEN installing the CLI THEN users SHALL be able to install via pipx or a Homebrew tap
- WHEN installing the GUI THEN users SHALL be able to drag-and-drop the .app and have it call the CLI
- WHEN running the GUI for the first time THEN the app SHALL check for the CLI and guide installation if missing

Requirement 10: Safety & Error Handling
Phase: MVP-CLI

User Story: As an operator, I want clear errors and safe shutdown so that I avoid dangling processes and vague failures.

Acceptance Criteria
- WHEN `llama-server` is missing THEN the system SHALL provide a specific error and guidance
- WHEN a port is busy THEN the system SHALL refuse to start and explain the conflict
- WHEN stopping a model THEN the system SHALL confirm termination or report a timeout and next steps

Requirement 11: Preferences & Paths
Phase: MVP-GUI

User Story: As a GUI user, I want to configure paths and intervals so that the tool fits my environment.

Acceptance Criteria
- WHEN I set a custom `llama_server_path` THEN the GUI and CLI SHALL use it for subsequent actions
- WHEN I change `log_dir` or refresh interval THEN the system SHALL persist and apply these settings

Requirement 12: Security Defaults
Phase: MVP-CLI

User Story: As a security-conscious user, I want safe defaults so that models are not exposed inadvertently.

Acceptance Criteria
- WHEN starting a model without explicit host THEN the system SHALL bind to `127.0.0.1`
- WHEN a user attempts to bind to `0.0.0.0` THEN the system SHALL warn and require explicit confirmation or flag

## 4. Non-Functional Requirements
- Clear CLI usage with helpful `--help` output
- Minimal dependencies; prefer Python standard library where feasible
- Fast startup (<1s) and low CPU overhead when idle
- Safe shutdown handling to avoid orphaned processes
- Config and logs under `~/Library/Application Support/llamaCPPManager` and `~/Library/Logs/llamaCPPManager` by default

Requirement 13: Container Deployment Support
Phase: MVP-Containers

User Story: As a user with Docker/Colima setup, I want to deploy models in containers so that I can isolate resources, manage dependencies consistently, and enable easier scaling.

Acceptance Criteria
- WHEN I configure a model with `--container` flag THEN the system SHALL build and run the model in a Docker container
- WHEN starting containerized models THEN the system SHALL mount model files as volumes and manage port mapping
- WHEN I run `status` THEN the system SHALL detect both bare-metal and containerized models with appropriate indicators
- WHEN using container mode THEN the system SHALL validate Docker availability and provide clear error messages if missing
- WHEN I run `container build` THEN the system SHALL create optimized Docker images for llama.cpp models
- WHEN I deploy multiple models THEN the system SHALL support Docker Compose orchestration for multi-model setups

Requirement 14: Multi-Scenario Deployment Support
Phase: MVP-Containers

User Story: As a user with different environments, I want to choose the deployment scenario that fits my infrastructure (macOS bare-metal, macOS containers, or remote Kubernetes) so that I can optimize for my specific use case.

Acceptance Criteria
- WHEN I configure a model THEN the system SHALL support selecting deployment scenario: `bare-metal`, `container`, or `kubernetes`
- WHEN using macOS scenarios THEN the system SHALL manage models on the local M4 Max device efficiently
- WHEN using Kubernetes scenario THEN the system SHALL deploy to remote Ubuntu OpenStack clusters
- WHEN switching scenarios THEN the system SHALL provide migration tools and clear guidance
- WHEN managing different scenarios THEN the system SHALL maintain consistent CLI interface across all deployment types

Requirement 15: Container Resource Management
Phase: MVP-Containers

User Story: As a resource-conscious user, I want to control container resource limits so that models don't consume excessive system resources.

Acceptance Criteria
- WHEN configuring containerized models THEN the system SHALL allow setting memory limits, CPU limits, and GPU access
- WHEN containers exceed limits THEN the system SHALL restart them gracefully and log the incidents
- WHEN I run `status --resources` THEN the system SHALL show resource usage for both containerized and bare-metal models
- WHEN Docker daemon is unavailable THEN the system SHALL gracefully fall back to bare-metal mode with user notification

Requirement 16: Kubernetes Deployment Support
Phase: MVP-K8s

User Story: As a user with Kubernetes clusters, I want to deploy models to Kubernetes so that I can leverage advanced orchestration, scaling, and resource management capabilities.

Acceptance Criteria
- WHEN I configure a model with `--kubernetes` flag THEN the system SHALL generate and apply Kubernetes manifests (Deployment, Service, ConfigMap)
- WHEN deploying to Kubernetes THEN the system SHALL support multiple deployment strategies (local cluster, remote cluster via kubectl context)
- WHEN managing K8s deployments THEN the system SHALL integrate with kubectl for status checks and log retrieval
- WHEN scaling models THEN the system SHALL support horizontal pod autoscaling based on CPU/memory metrics
- WHEN I run `status` THEN the system SHALL detect and report on bare-metal, container, and Kubernetes-deployed models
- WHEN using persistent volumes THEN the system SHALL manage model file storage via PVC for efficient sharing across pods

Requirement 17: Unified Model Management
Phase: MVP-ModelManager

User Story: As a user managing multiple models, I want a unified interface that works for both native and containerized deployments so that I can choose the best deployment method for each use case.

Acceptance Criteria
- WHEN I configure a model THEN the system SHALL support deployment_type: native or container
- WHEN I start a model THEN the system SHALL use the configured deployment type transparently
- WHEN I define model groups THEN the system SHALL support mutual exclusion (only one model in group runs at a time)
- WHEN switching between models in an exclusive group THEN the system SHALL automatically stop the previous model
- WHEN a model is in a group THEN the system SHALL display group membership in status output
- WHEN models have no autostart THEN the system SHALL support on-demand launching for all models

Requirement 18: Large Coding Model Support
Phase: MVP-CodingModels

User Story: As a developer, I want to run large coding models (Qwen Coder, DeepSeek Coder) on-demand so that I can use them for complex code generation without keeping them running constantly.

Acceptance Criteria
- WHEN I download a coding model THEN the system SHALL support downloading from Hugging Face with progress tracking
- WHEN I launch a coding model THEN the system SHALL start it natively with appropriate resource allocation
- WHEN a coding model is idle THEN the system SHALL optionally auto-stop it after configurable timeout
- WHEN I query via MCP THEN the system SHALL support launching coding models on-demand from AI assistants
- WHEN multiple coding models exist THEN the system SHALL enforce mutual exclusion to prevent memory exhaustion
- WHEN I check status THEN the system SHALL show model size, RAM requirements, and use case metadata

Requirement 19: Flexible Deployment Architecture
Phase: MVP-ModelManager

User Story: As a user with different needs, I want models to work natively by default with optional container support so that I get the best performance while maintaining deployment flexibility.

Acceptance Criteria
- WHEN no deployment_type is specified THEN the system SHALL default to native deployment
- WHEN containers are not available THEN the system SHALL still work with native deployment
- WHEN I migrate a model to containers THEN the system SHALL support changing deployment_type without data loss
- WHEN using native deployment THEN the system SHALL provide equivalent CLI/GUI/MCP interfaces as containerized
- WHEN both native and containerized models exist THEN the system SHALL manage them uniformly
- WHEN deployment_type changes THEN the system SHALL validate resources and provide clear migration guidance

## 5. Stretch Goals (Optional)
- macOS menu bar advanced features (quick prompts, Raycast integration)
- Prometheus endpoint exposing metrics
- Quick actions to switch model quantizations or update binaries
- Workspace profiles (switch between dev/prod model sets)
- Multi-cloud Kubernetes support (EKS, GKE, AKS)
- GitOps integration for declarative model deployments
- Auto-scaling based on request load and resource utilization

## 6. Open Questions
- Preferred packaging for GUI (App Store vs. downloadable .dmg)
- Whether the GUI should edit YAML directly or rely solely on CLI `config set`
- Need for remote host support or SSH tunnels in a later phase

Update this document as requirements evolve.
