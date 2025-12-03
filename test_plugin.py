#!/usr/bin/env python3
"""Test script to debug the compression plugin."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tensorboard.backend.event_processing import event_multiplexer as em
from compression_board_plugin.compression_board_plugin.compression_plugin import CompressionPlugin

# Build multiplexer
m = em.EventMultiplexer()
m.AddRunsFromDirectory('runs/compression_benchmark/all_models_benchmark_100epochs_SANITYCHECK')
m.Reload()

class Ctx:
    def __init__(self):
        self.multiplexer = m
        self.logdir = 'runs/compression_benchmark/all_models_benchmark_100epochs_SANITYCHECK'

ctx = Ctx()
plugin = CompressionPlugin(ctx)

print("is_active:", plugin.is_active())
print()

# Test the summary endpoint
class Req:
    pass

req = Req()
try:
    resp = plugin._serve_summary(req)
    print("Response type:", type(resp))
    if hasattr(resp, 'data'):
        import json
        data = json.loads(resp.data)
        print("Models found:", len(data.get('models', [])))
        if data.get('error'):
            print("ERROR:", data['error'])
            if 'traceback' in data:
                print("\nTraceback:")
                print(data['traceback'])
        else:
            print("First model:", data['models'][0] if data['models'] else None)
except Exception as e:
    import traceback
    print("EXCEPTION:", e)
    traceback.print_exc()

