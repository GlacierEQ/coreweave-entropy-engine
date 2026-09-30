# coreweave-entropy-engine

> GPU rack power management, thermal throttle detection, job scheduling with preemption, and cluster utilization metrics.

**Domain:** Datacenter Compute & GPU Cluster Orchestration
**Company Orbit:** CoreWeave

## Architecture

```
src/coreweave_entropy_engine/
├── __init__.py
└── core.py          # Datacenter Compute & GPU Cluster Orchestration implementation
tests/
└── test_gpu_cluster.py
.github/workflows/
└── ci.yml           # Automated CI enforcement
```

## Quick Start

```bash
# Run tests
PYTHONPATH=src pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Key Classes

| Class | Purpose |
|-------|---------|
| `GPUCluster` | GPU cluster resource management and scheduling. |

## License

MIT
