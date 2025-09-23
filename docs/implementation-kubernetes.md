# Kubernetes Implementation Plan

## Phase 1: Core K8s Integration (MVP-K8s)

### 1.1 Prerequisites & Dependencies
- **New Dependencies**: Add to `pyproject.toml`
  - `kubernetes>=28.1.0` - Official Kubernetes Python client
  - `pyyaml>=6.0` - YAML manifest generation (already present)
  - `jinja2>=3.1.0` - Template rendering for manifests

### 1.2 New Module: `src/llamacpp_manager/kubernetes.py`

```python
# Core classes and functions to implement:

class KubernetesManager:
    """Handles all Kubernetes operations for llamaCPPManager"""

    def __init__(self, config_dir: str, log_dir: str):
        self.config_dir = config_dir
        self.log_dir = log_dir
        self.k8s_client = None

    def validate_prerequisites(self) -> bool:
        """Check kubectl availability and cluster connectivity"""

    def deploy_model(self, model_config: dict) -> dict:
        """Deploy a model to Kubernetes cluster"""

    def generate_manifests(self, model_config: dict) -> dict:
        """Generate K8s manifests from model config"""

    def apply_manifests(self, manifests: dict, namespace: str) -> bool:
        """Apply manifests to cluster"""

    def scale_deployment(self, name: str, replicas: int) -> bool:
        """Scale model deployment"""

    def get_model_status(self, name: str) -> dict:
        """Get comprehensive status of K8s deployment"""

    def cleanup_model(self, name: str) -> bool:
        """Remove all K8s resources for a model"""
```

### 1.3 CLI Command Extensions

Add new subcommand group `k8s` to `src/llamacpp_manager/cli.py`:

```python
# New CLI commands to implement:

@click.group()
def k8s():
    """Kubernetes deployment commands"""
    pass

@k8s.command()
@click.argument('name')
@click.option('--replicas', type=int, help='Number of replicas')
def scale(name: str, replicas: int):
    """Scale a Kubernetes deployment"""

@k8s.command()
@click.argument('name')
@click.option('--context', help='Kubectl context to use')
def status(name: str, context: str):
    """Show Kubernetes-specific status"""

@k8s.command()
@click.argument('name')
@click.option('--follow', '-f', is_flag=True)
def logs(name: str, follow: bool):
    """Get logs from Kubernetes pods"""

@k8s.command()
@click.argument('name')
@click.option('--output', '-o', help='Output directory for manifests')
def manifest(name: str, output: str):
    """Generate manifests without applying"""

@k8s.command()
@click.argument('name')
def cleanup(name: str):
    """Remove all Kubernetes resources for a model"""
```

### 1.4 Configuration Schema Updates

Extend `config.py` schema validation:

```python
# Add to model schema validation:
kubernetes_schema = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "default": "llamacpp-models"},
        "replicas": {
            "type": "object",
            "properties": {
                "initial": {"type": "integer", "minimum": 1, "default": 1},
                "min": {"type": "integer", "minimum": 1, "default": 1},
                "max": {"type": "integer", "minimum": 1, "default": 5}
            }
        },
        "resources": {
            "type": "object",
            "properties": {
                "requests": {"type": "object"},
                "limits": {"type": "object"}
            }
        },
        "context": {"type": "string"},
        "image": {
            "type": "object",
            "properties": {
                "registry": {"type": "string"},
                "repository": {"type": "string", "default": "llama-server"},
                "tag": {"type": "string", "default": "latest"}
            }
        }
    }
}
```

## Phase 2: Manifest Templates & Generation

### 2.1 Template System
Create `templates/kubernetes/` directory with Jinja2 templates:

```
templates/kubernetes/
├── deployment.yaml.j2
├── service.yaml.j2
├── hpa.yaml.j2
├── configmap.yaml.j2
├── pvc.yaml.j2
└── namespace.yaml.j2
```

### 2.2 Template Engine Implementation

```python
class ManifestGenerator:
    """Generate Kubernetes manifests from templates"""

    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def render_deployment(self, model_config: dict) -> str:
        """Render deployment manifest"""

    def render_service(self, model_config: dict) -> str:
        """Render service manifest"""

    def render_hpa(self, model_config: dict) -> str:
        """Render HPA manifest"""

    def render_all(self, model_config: dict) -> dict:
        """Render all manifests for a model"""
```

## Phase 3: Status Integration

### 3.1 Update `discovery.py`
Add Kubernetes discovery to existing status detection:

```python
def discover_kubernetes_models(config: dict) -> List[dict]:
    """Discover models running in Kubernetes"""
    # Use kubectl or K8s API to find deployments
    # Return status in standard format
```

### 3.2 Update `health.py`
Add K8s health checking:

```python
def check_kubernetes_health(model_config: dict) -> dict:
    """Check health of K8s-deployed model"""
    # Check service endpoints, pod readiness
    # Return standard health format
```

## Phase 4: Testing Strategy

### 4.1 Unit Tests
Create `tests/test_kubernetes.py`:

```python
class TestKubernetesManager:
    def test_manifest_generation(self):
        """Test manifest generation from config"""

    def test_validate_prerequisites(self):
        """Test kubectl and cluster validation"""

    def test_deployment_scaling(self):
        """Test scaling operations"""

    @pytest.mark.integration
    def test_full_deployment_cycle(self):
        """Test deploy -> status -> cleanup cycle"""
```

### 4.2 Integration Tests
- Local kind/k3s cluster setup
- CI/CD pipeline with test cluster
- Mock kubectl responses for offline testing

## Phase 5: Documentation & Examples

### 5.1 User Documentation
Update `README.md` with K8s examples:

```bash
# Deploy to Kubernetes
llamacpp-manager config add mymodel ~/models/model.gguf --port 8080 --kubernetes
llamacpp-manager start mymodel

# Scale deployment
llamacpp-manager k8s scale mymodel --replicas 3

# Monitor status
llamacpp-manager status --kubernetes
```

### 5.2 Example Configurations
Create `examples/kubernetes/` with:
- Basic single-model deployment
- Multi-model with resource limits
- Production-ready with monitoring
- Multi-cluster federation example

## Implementation Timeline

### Week 1: Foundation
- [ ] Add dependencies to pyproject.toml
- [ ] Create kubernetes.py module skeleton
- [ ] Implement basic manifest generation
- [ ] Add kubectl validation

### Week 2: Core Features
- [ ] Implement deploy_model() method
- [ ] Add CLI k8s subcommands
- [ ] Create manifest templates
- [ ] Basic status integration

### Week 3: Advanced Features
- [ ] Scaling operations
- [ ] Enhanced status reporting
- [ ] Log aggregation from pods
- [ ] Resource management

### Week 4: Testing & Polish
- [ ] Comprehensive unit tests
- [ ] Integration test setup
- [ ] Documentation updates
- [ ] Example configurations

## Risk Mitigation

### Complexity Management
- Start with minimal viable K8s integration
- Use existing patterns from container.py
- Leverage proven libraries (official K8s client)

### Dependency Management
- Pin K8s client versions for stability
- Graceful degradation when kubectl unavailable
- Clear error messages for missing prerequisites

### User Experience
- Maintain consistent CLI patterns
- Provide migration path from container deployments
- Comprehensive validation and helpful error messages

## Success Criteria

1. **Functional**: Deploy, scale, monitor K8s models via CLI
2. **Reliable**: Graceful error handling and recovery
3. **Performant**: Fast status checks and deployment operations
4. **Maintainable**: Clean code following existing patterns
5. **Documented**: Clear examples and troubleshooting guides