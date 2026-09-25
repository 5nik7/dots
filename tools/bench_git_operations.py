#!/usr/bin/env python3
"""Sequential warm status observations in disposable trees, not timing gates."""
import json
import statistics
import time
from test_git_operations import GitOperations


def main():
    fixture = GitOperations()
    fixture.setUp()
    try:
        child = fixture.repo('dependency')
        results = []
        for count in (0, 4, 9):
            root = fixture.repo('root-' + str(count))
            for i in range(count):
                fixture.sub(root, child, 'modules/child-' + str(i))
            fixture.cli(root, 'status', '--json')
            samples = []
            for _ in range(3):
                start = time.perf_counter()
                fixture.cli(root, 'status', '--json')
                samples.append((time.perf_counter() - start) * 1000)
            results.append({'repositories': count + 1, 'samples_ms': samples,
                            'median_ms': statistics.median(samples)})
        print(json.dumps({'scope': 'warm native status; 3 samples; no cold-start claim', 'results': results}, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
