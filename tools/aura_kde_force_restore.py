#!/usr/bin/env python3
"""Force restore wallpaper without state validation - for autostart"""
import sys
import json
import time
from pathlib import Path
from aura_kde_v2 import snapshot, transition, validate, normalized

def force_restore(operation_file):
    """Apply wallpaper from operation file, ignoring current state"""
    # Read operation
    with open(operation_file) as f:
        record = json.load(f)

    if record.get('schema') != 2:
        raise ValueError('Expected a v2 record')

    # Get desired state from the operation
    desired = record['after']
    validate(desired)

    # Get current state (just for logging, not validation)
    current = snapshot()

    print(f"Current plugin: {current['targets'][0]['plugin']}", file=sys.stderr)
    print(f"Desired plugin: {desired['targets'][0]['plugin']}", file=sys.stderr)

    # Check if plugin change is needed
    needs_blank = any(
        t1['plugin'] != t2['plugin']
        for t1, t2 in zip(current['targets'], desired['targets'])
    )

    if needs_blank:
        print("Plugin change needed, using blank transition", file=sys.stderr)
        # Import blank_state here to avoid circular import
        from aura_kde_v2 import blank_state
        stage = blank_state(desired)
        transition(current, stage)
        transition(stage, desired)
    else:
        print("Same plugin, direct transition", file=sys.stderr)
        transition(current, desired)

    # Verify it worked
    final = snapshot()
    final_plugin = final['targets'][0]['plugin']
    desired_plugin = desired['targets'][0]['plugin']

    if final_plugin == desired_plugin:
        print(f"✓ Successfully applied: {desired_plugin}", file=sys.stderr)
        return True
    else:
        print(f"✗ Failed: plugin is {final_plugin}, expected {desired_plugin}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: aura_kde_force_restore.py <operation.json>", file=sys.stderr)
        sys.exit(1)

    try:
        success = force_restore(sys.argv[1])
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
