#!/usr/bin/env python3
"""Debug script to see what tags are in the runs."""

import sys
sys.path.insert(0, '/media/volume/volume-dev/projects/tensorboard-compression-engine')

from tensorboard.backend.event_processing import event_multiplexer as em

m = em.EventMultiplexer()
m.AddRunsFromDirectory('runs/compression_benchmark/all_models_benchmark_100epochs_SANITYCHECK')
m.Reload()

runs = m.Runs()
print(f"Total runs: {len(runs)}")
print()

for run_name, run_info in list(runs.items())[:3]:  # First 3 runs
    print(f"Run: {run_name}")
    tags = run_info.get("scalars", [])
    print(f"  Total scalar tags: {len(tags)}")
    compression_tags = [t for t in tags if "compression/" in t]
    print(f"  Compression tags: {len(compression_tags)}")
    if compression_tags:
        print(f"  Examples: {compression_tags[:3]}")
    print()

