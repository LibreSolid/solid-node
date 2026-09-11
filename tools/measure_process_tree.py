"""Run one command inside an externally limited cgroup and record its real peak.

Invoke under systemd-run with MemoryMax and MemorySwapMax; this wrapper does
not claim to impose a cap itself. The kernel peak includes the wrapper, every
descendant, charged page cache and kernel memory, not just Python's heap/RSS.
"""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=pathlib.Path)
    parser.add_argument('--log', required=True, type=pathlib.Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    relative = pathlib.Path('/proc/self/cgroup').read_text().strip().split('0::')[1]
    group = pathlib.Path('/sys/fs/cgroup') / relative.lstrip('/')
    read = lambda name: (group / name).read_text().strip()
    cap = int(read('memory.max'))
    assert cap == 8_000_000_000 and read('memory.swap.max') == '0'
    framework = pathlib.Path(os.environ['PYTHONPATH'])
    def source_hash():
        digest = hashlib.sha256()
        for source in sorted((framework / 'solid_node').rglob('*.py')):
            digest.update(str(source.relative_to(framework)).encode() + b'\0')
            digest.update(source.read_bytes())
        return digest.hexdigest()
    before = source_hash()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with args.log.open('w') as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
    peak = int(read('memory.peak'))
    report = dict(command=command, returncode=result.returncode,
                  framework=str(framework), framework_source_sha256=before,
                  framework_unchanged=before == source_hash(),
                  elapsed_seconds=time.monotonic() - start,
                  cgroup=str(group), memory_max_bytes=cap,
                  memory_peak_bytes=peak, memory_peak_MiB=peak / 2**20,
                  memory_peak_GiB=peak / 2**30,
                  cap_headroom_bytes=cap-peak,
                  swap_peak_bytes=int(read('memory.swap.peak')),
                  memory_events=read('memory.events'))
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
