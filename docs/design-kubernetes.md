# llamaCPPManager — Kubernetes Design

## Overview
Kubernetes deployment strategy for llamaCPPManager, enabling scalable, cloud-native deployments of llama.cpp models with advanced orchestration capabilities.

## Kubernetes Architecture

```mermaid
graph TD
  subgraph Local_macOS
    CLI[llamacpp-manager CLI]
    CLI --> K8S[kubernetes.py]
    K8S --> KUBECTL[kubectl client]
    K8S --> KAPI[Kubernetes API]
  end

  subgraph Kubernetes_Cluster
    KAPI --> NS[llamacpp-models namespace]

    subgraph Model_Deployments
      NS --> DEP1[Deployment: smollm3]
      NS --> DEP2[Deployment: mistral7b]
      NS --> DEP3[Deployment: phi3]
    end

    subgraph Services_Networking
      DEP1 --> SVC1[Service: smollm3-svc]
      DEP2 --> SVC2[Service: mistral7b-svc]
      DEP3 --> SVC3[Service: phi3-svc]

      SVC1 --> ING[Ingress Controller]
      SVC2 --> ING
      SVC3 --> ING
    end

    subgraph Storage
      NS --> PVC1[PVC: model-storage]
      PVC1 --> PV[Persistent Volume]
      DEP1 --> PVC1
      DEP2 --> PVC1
      DEP3 --> PVC1
    end

    subgraph Scaling_Monitoring
      DEP1 --> HPA1[HPA: smollm3-hpa]
      DEP2 --> HPA2[HPA: mistral7b-hpa]
      DEP3 --> HPA3[HPA: phi3-hpa]

      HPA1 --> METRICS[Metrics Server]
      HPA2 --> METRICS
      HPA3 --> METRICS
    end
  end

  subgraph External_Access
    ING --> LB[Load Balancer]
    LB --> USERS[External Users]
  end
```

## Deployment Flow

```mermaid
sequenceDiagram
  participant User
  participant CLI as llamacpp-manager
  participant K8S as kubernetes.py
  participant KUBECTL as kubectl
  participant CLUSTER as K8s Cluster
  participant REGISTRY as Container Registry

  User->>CLI: start model-name --kubernetes
  CLI->>K8S: deploy_model(config)
  K8S->>K8S: generate_manifests()

  Note over K8S: Generate Deployment, Service, ConfigMap, PVC

  K8S->>KUBECTL: apply -f deployment.yaml
  KUBECTL->>CLUSTER: Create Deployment
  CLUSTER->>REGISTRY: Pull llama-server image
  REGISTRY-->>CLUSTER: Image layers

  CLUSTER->>CLUSTER: Mount PVC with models
  CLUSTER->>CLUSTER: Start pods

  K8S->>KUBECTL: apply -f service.yaml
  KUBECTL->>CLUSTER: Create Service

  K8S->>KUBECTL: apply -f hpa.yaml
  KUBECTL->>CLUSTER: Create HPA

  K8S-->>CLI: Deployment successful
  CLI-->>User: Model deployed to K8s
```

## Manifest Templates

### Deployment Template
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {model_name}
  namespace: llamacpp-models
  labels:
    app: llamacpp-server
    model: {model_name}
    managed-by: llamacpp-manager
spec:
  replicas: {initial_replicas}
  selector:
    matchLabels:
      app: llamacpp-server
      model: {model_name}
  template:
    metadata:
      labels:
        app: llamacpp-server
        model: {model_name}
    spec:
      containers:
      - name: llama-server
        image: {registry}/llama-server:{tag}
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: MODEL_PATH
          value: "/models/{model_file}"
        - name: PORT
          value: "8080"
        resources:
          requests:
            memory: {memory_request}
            cpu: {cpu_request}
          limits:
            memory: {memory_limit}
            cpu: {cpu_limit}
        volumeMounts:
        - name: model-storage
          mountPath: /models
          readOnly: true
        - name: config
          mountPath: /config
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /v1/models
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 5
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: model-storage
      - name: config
        configMap:
          name: {model_name}-config
```

### Service Template
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {model_name}-svc
  namespace: llamacpp-models
  labels:
    app: llamacpp-server
    model: {model_name}
spec:
  selector:
    app: llamacpp-server
    model: {model_name}
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  type: ClusterIP
```

### HPA Template
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {model_name}-hpa
  namespace: llamacpp-models
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {model_name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Configuration Schema Extensions

```yaml
models:
  - name: smollm3
    model_path: /Users/you/llms/smollm3/SmolLM3-Q8_0.gguf
    deployment_mode: kubernetes  # bare-metal | container | kubernetes
    kubernetes:
      namespace: llamacpp-models
      replicas:
        initial: 1
        min: 1
        max: 5
      resources:
        requests:
          memory: "2Gi"
          cpu: "500m"
        limits:
          memory: "4Gi"
          cpu: "2"
      storage:
        pvc_name: model-storage
        mount_path: /models
      image:
        registry: "localhost:5000"
        repository: "llama-server"
        tag: "latest"
      context: "local-cluster"  # kubectl context
      ingress:
        enabled: true
        host: "smollm3.local.dev"
        tls: false
```

## CLI Command Extensions

```bash
# Deploy to Kubernetes
llamacpp-manager start smollm3 --kubernetes

# Scale deployment
llamacpp-manager k8s scale smollm3 --replicas 3

# Show K8s-specific status
llamacpp-manager status --kubernetes
llamacpp-manager k8s status smollm3

# Get logs from K8s pods
llamacpp-manager k8s logs smollm3 --follow

# Build and push container image
llamacpp-manager k8s build smollm3 --push

# Deploy with custom context
llamacpp-manager start smollm3 --kubernetes --context production-cluster

# Generate manifests without applying
llamacpp-manager k8s manifest smollm3 --output ./manifests/

# Clean up K8s resources
llamacpp-manager k8s cleanup smollm3
```

## Status Integration

Enhanced status output for Kubernetes deployments:

```json
{
  "models": [
    {
      "name": "smollm3",
      "deployment_mode": "kubernetes",
      "status": "running",
      "kubernetes": {
        "namespace": "llamacpp-models",
        "context": "local-cluster",
        "replicas": {
          "desired": 2,
          "ready": 2,
          "available": 2
        },
        "service": {
          "name": "smollm3-svc",
          "cluster_ip": "10.96.45.123",
          "port": 80
        },
        "pods": [
          {
            "name": "smollm3-7d4b8f5c6d-abc12",
            "status": "Running",
            "node": "worker-1",
            "ready": true
          },
          {
            "name": "smollm3-7d4b8f5c6d-def34",
            "status": "Running",
            "node": "worker-2",
            "ready": true
          }
        ],
        "hpa": {
          "enabled": true,
          "current_replicas": 2,
          "target_cpu": 70,
          "current_cpu": 45
        }
      },
      "health": {
        "reachable": true,
        "latency_ms": 23,
        "endpoint": "http://smollm3.local.dev/v1/models"
      }
    }
  ]
}
```

## Security Considerations

1. **RBAC**: Create service accounts with minimal permissions
2. **Network Policies**: Restrict pod-to-pod communication
3. **Secrets Management**: Store sensitive configs in K8s Secrets
4. **Image Security**: Use distroless base images and scan for vulnerabilities
5. **Resource Limits**: Prevent resource exhaustion attacks

## Multi-Cluster Support

- Support multiple kubectl contexts
- Cluster-specific configuration profiles
- Cross-cluster model federation for load distribution
- Disaster recovery with automatic failover

## Integration Points

- **GitOps**: Generate manifests compatible with ArgoCD/Flux
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Logging**: Structured logging with Fluentd/Fluent Bit
- **Service Mesh**: Istio integration for advanced traffic management