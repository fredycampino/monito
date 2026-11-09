"""Run both services; stop the container if either child exits."""
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

children = []
stopping = False


def stop(signum, frame):
    global stopping
    stopping = True


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, stop)

# Keep code immutable; only project metadata and extension cache are writable.
Path(os.environ['HOME']).mkdir(parents=True, exist_ok=True)
project = Path('/tmp/mobile')
project.mkdir(exist_ok=True)
Path('/tmp/mobile-cache').mkdir(exist_ok=True)
shutil.copyfile('/opt/mobile/package.json', project / 'package.json')
if not (project / 'node_modules').exists():
    (project / 'node_modules').symlink_to('/opt/mobile/node_modules')
os.environ.pop('APPIUM_HOME', None)
os.environ.pop('ADB_SERVER_SOCKET', None)
os.chdir(project)
exit_code = 0
try:
    children.append(subprocess.Popen(['adb', '-a', '-P', '5037', 'server', 'nodaemon']))
    children.append(subprocess.Popen([
        'node', '/opt/mobile/node_modules/appium/index.js',
        '--address', '0.0.0.0', '--port', '4723',
    ]))
    while not stopping:
        for child in children:
            if child.poll() is not None:
                exit_code = child.returncode or 1
                stopping = True
                break
        time.sleep(0.2)
finally:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
sys.exit(exit_code)
