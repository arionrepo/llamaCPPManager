# Container Implementation Plan

## Phase 1: Docker Foundation (MVP-Containers)

### 1.1 Prerequisites & Dependencies
- **New Dependencies**: Add to `pyproject.toml`
  - `docker>=6.1.0` - Official Docker Python client
  - `PyYAML>=6.0` - Docker Compose generation (already present)

### 1.2 New Module: `src/llamacpp_manager/container.py`

```python
# Core classes and functions to implement:

class ContainerManager:
    """Handles all Docker operations for llamaCPPManager"""

    def __init__(self, config_dir: str, log_dir: str):
        self.config_dir = config_dir
        self.log_dir = log_dir
        self.docker_client = None

    def validate_docker(self) -> bool:
        """Check Docker daemon availability"""

    def build_image(self, model_config: dict) -> str:
        """Build Docker image for llama.cpp model"""

    def start_container(self, model_config: dict) -> dict:
        """Start model in Docker container"""

    def stop_container(self, name: str) -> bool:
        """Stop and remove container"""

    def get_container_status(self, name: str) -> dict:
        """Get container status and resource usage"""

    def get_container_logs(self, name: str, tail: int = 100) -> str:
        """Retrieve container logs"""

    def cleanup_resources(self, name: str) -> bool:
        """Clean up container and associated resources"""
```

### 1.3 CLI Command Extensions

Add new subcommand group `container` to `src/llamacpp_manager/cli.py`:

```python
# New CLI commands to implement:

@click.group()
def container():
    """Container deployment commands"""
    pass

@container.command()
@click.argument('name')
@click.option('--push', is_flag=True, help='Push to registry after build')
def build(name: str, push: bool):
    """Build Docker image for a model"""

@container.command()
@click.argument('name')
@click.option('--tail', type=int, default=100, help='Number of log lines')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(name: str, tail: int, follow: bool):
    """Get container logs"""

@container.command()
@click.argument('name')
def cleanup(name: str):
    """Remove container and associated resources"""

@container.command()
def ps():
    """List all llamaCPP containers"""
```

### 1.4 Configuration Schema Updates

Extend `config.py` schema validation:

```python
# Add to model schema validation:
container_schema = {
    "type": "object",
    "properties": {
        "image": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tag": {"type": "string", "default": "latest"},
                "registry": {"type": "string"}
            }
        },
        "resources": {
            "type": "object",
            "properties": {
                "memory": {"type": "string", "default": "2g"},
                "cpus": {"type": "string", "default": "1.0"},
                "gpus": {"type": "string"}
            }
        },
        "volumes": {
            "type": "object",
            "properties": {
                "model_path": {"type": "string"},
                "cache_path": {"type": "string"}
            }
        },
        "network": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "default": "bridge"},
                "port_mapping": {"type": "object"}
            }
        }
    }
}

# Update deployment_mode enum
deployment_mode_schema = {
    "type": "string",
    "enum": ["bare-metal", "container", "kubernetes"],
    "default": "bare-metal"
}
```

## Phase 2: Dockerfile & Image Management

### 2.1 Create Docker Templates
Create `docker/` directory structure:

```
docker/
├── Dockerfile
├── Dockerfile.alpine
├── Dockerfile.ubuntu
├── docker-compose.template.yml
└── scripts/
    ├── entrypoint.sh
    └── healthcheck.sh
```

### 2.2 Dockerfile Implementation

```dockerfile
# docker/Dockerfile (optimized for production)
FROM alpine:3.19 AS builder

# Install build dependencies
RUN apk add --no-cache \
    git cmake make g++ pkgconfig linux-headers

# Build llama.cpp
WORKDIR /build
RUN git clone https://github.com/ggerganov/llama.cpp.git . && \
    git checkout b4226
RUN cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=OFF \
    -DGGML_STATIC=ON \
    -DLLAMA_STATIC=ON && \
    cmake --build build --config Release --target llama-server -j$(nproc)

# Runtime stage
FROM alpine:3.19

RUN apk add --no-cache libgcc libstdc++ ca-certificates curl
RUN addgroup -g 1000 llama && adduser -D -s /bin/sh -u 1000 -G llama llama

COPY --from=builder /build/build/bin/llama-server /usr/local/bin/
COPY docker/scripts/entrypoint.sh /usr/local/bin/
COPY docker/scripts/healthcheck.sh /usr/local/bin/

RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh
RUN mkdir -p /models /logs && chown -R llama:llama /models /logs

USER llama
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

### 2.3 Image Builder Implementation

```python
class ImageBuilder:
    """Builds optimized Docker images for llama.cpp models"""

    def __init__(self, docker_client):
        self.docker_client = docker_client

    def build_base_image(self) -> str:
        """Build base llama.cpp image"""

    def build_model_image(self, model_config: dict) -> str:
        """Build model-specific image with optimizations"""

    def push_image(self, image_name: str, registry: str) -> bool:
        """Push image to registry"""

    def cleanup_build_cache(self) -> None:
        """Clean up Docker build cache"""
```

## Phase 3: Docker Compose Integration

### 3.1 Compose Template System

```yaml
# docker/docker-compose.template.yml
version: '3.8'

services:
  {{ model_name }}:
    image: {{ image_name }}:{{ tag }}
    container_name: llamacpp-{{ model_name }}
    restart: unless-stopped
    ports:
      - "{{ host_port }}:8080"
    volumes:
      - "{{ model_path }}:/models/{{ model_file }}:ro"
      - "llamacpp-{{ model_name }}-logs:/logs"
    environment:
      - MODEL_PATH=/models/{{ model_file }}
      - PORT=8080
      {% for key, value in env_vars.items() %}
      - {{ key }}={{ value }}
      {% endfor %}
    deploy:
      resources:
        limits:
          memory: {{ memory_limit }}
          cpus: '{{ cpu_limit }}'
        reservations:
          memory: {{ memory_request }}
          cpus: '{{ cpu_request }}'
    networks:
      - llamacpp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  llamacpp-{{ model_name }}-logs:
    driver: local

networks:
  llamacpp-network:
    driver: bridge
```

### 3.2 Compose Manager Implementation

```python
class ComposeManager:
    """Manages Docker Compose deployments for multi-model setups"""

    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.compose_file = f"{config_dir}/docker-compose.yml"

    def generate_compose_file(self, models: List[dict]) -> str:
        """Generate docker-compose.yml for all container models"""

    def start_services(self, service_names: List[str] = None) -> bool:
        """Start Docker Compose services"""

    def stop_services(self, service_names: List[str] = None) -> bool:
        """Stop Docker Compose services"""

    def get_services_status(self) -> dict:
        """Get status of all Compose services"""

    def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a specific service"""
```

## Phase 4: Status & Discovery Integration

### 4.1 Update `discovery.py`
Add container discovery to existing status detection:

```python
def discover_container_models(config: dict) -> List[dict]:
    """Discover models running in Docker containers"""
    # Use Docker API to find containers with llamacpp labels
    # Return status in standard format

def discover_compose_models(config: dict) -> List[dict]:
    """Discover models managed by Docker Compose"""
    # Parse docker-compose.yml and check service status
    # Return status in standard format
```

### 4.2 Update `health.py`
Add container health checking:

```python
def check_container_health(model_config: dict) -> dict:
    """Check health of containerized model"""
    # Check container status, resource usage, port accessibility
    # Return standard health format

def get_container_metrics(container_name: str) -> dict:
    """Get resource usage metrics from container"""
    # CPU, memory, network usage
```

### 4.3 Enhanced Status Output

```json
{
  "models": [
    {
      "name": "smollm3",
      "deployment_mode": "container",
      "status": "running",
      "container": {
        "id": "abc123def456",
        "image": "llamacpp-smollm3:latest",
        "created": "2024-01-15T10:30:00Z",
        "ports": {
          "8080/tcp": "127.0.0.1:8081"
        },
        "resources": {
          "memory_usage": "1.2GB",
          "memory_limit": "2GB",
          "cpu_usage": "45%",
          "cpu_limit": "1.0"
        },
        "volumes": [
          "/Users/you/llms/smollm3/SmolLM3-Q8_0.gguf:/models/model.gguf:ro"
        ]
      },
      "health": {
        "reachable": true,
        "latency_ms": 12,
        "container_health": "healthy"
      }
    }
  ]
}
```

## Phase 5: Process Integration

### 5.1 Update `process.py`
Extend process management to handle containers:

```python
class ProcessManager:
    """Extended to handle bare-metal and container deployments"""

    def start_model(self, model_config: dict) -> dict:
        """Route to appropriate deployment mode"""
        deployment_mode = model_config.get('deployment_mode', 'bare-metal')

        if deployment_mode == 'container':
            return self.container_manager.start_container(model_config)
        elif deployment_mode == 'bare-metal':
            return self._start_bare_metal(model_config)
        else:
            raise ValueError(f"Unsupported deployment mode: {deployment_mode}")

    def stop_model(self, name: str, model_config: dict) -> bool:
        """Route to appropriate stop method"""

    def restart_model(self, name: str, model_config: dict) -> dict:
        """Route to appropriate restart method"""
```

## Phase 6: Testing Strategy

### 6.1 Unit Tests
Create `tests/test_container.py`:

```python
class TestContainerManager:
    def test_docker_validation(self):
        """Test Docker daemon connectivity"""

    def test_image_building(self):
        """Test Docker image building"""

    def test_container_lifecycle(self):
        """Test start/stop/restart cycle"""

    @pytest.mark.integration
    def test_compose_deployment(self):
        """Test Docker Compose multi-model deployment"""

class TestImageBuilder:
    def test_dockerfile_generation(self):
        """Test Dockerfile generation for different configurations"""

    def test_build_optimization(self):
        """Test build cache and layer optimization"""
```

### 6.2 Integration Tests
- Docker-in-Docker test environment
- Mock model files for testing
- Container resource limit validation
- Port conflict resolution testing

## Implementation Timeline

### Week 1: Foundation
- [ ] Add Docker dependency to pyproject.toml
- [ ] Create container.py module skeleton
- [ ] Implement Docker daemon validation
- [ ] Basic container start/stop functionality

### Week 2: Image Management
- [ ] Create Dockerfile templates
- [ ] Implement ImageBuilder class
- [ ] Add container build CLI commands
- [ ] Basic health checking for containers

### Week 3: Compose Integration
- [ ] Docker Compose template system
- [ ] ComposeManager implementation
- [ ] Multi-model container deployments
- [ ] Resource management and limits

### Week 4: Integration & Testing
- [ ] Status discovery integration
- [ ] Enhanced health checking
- [ ] Comprehensive unit tests
- [ ] Documentation and examples

## Risk Mitigation

### Resource Management
- Implement proper resource limits by default
- Monitor container resource usage
- Automatic cleanup of stopped containers

### Port Conflicts
- Automatic port discovery and mapping
- Validation against both bare-metal and container ports
- Clear error messages for conflicts

### Docker Availability
- Graceful fallback to bare-metal when Docker unavailable
- Clear error messages and troubleshooting guidance
- Optional dependency handling

## Success Criteria

1. **Functional**: Deploy, monitor, scale containerized models
2. **Reliable**: Robust error handling and resource management
3. **Performant**: Fast container operations and efficient resource usage
4. **Secure**: Container isolation and resource limits
5. **Maintainable**: Clean integration with existing codebase