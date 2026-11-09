"""Isolated image smoke test. No USB, network, live HOME or published ports."""
import json
import subprocess
import time
import uuid


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, text=True, capture_output=True)


name = 'mobile-ci-' + uuid.uuid4().hex[:12]
try:
    docker(
        'run', '-d', '--name', name, '--network', 'none', '--read-only',
        '--user', '10001:10001', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:mode=1777',
        '-e', 'HOME=/tmp/test-home', '--health-interval', '1s', 'monito-mobile:ci',
    )
    for _ in range(60):
        state = json.loads(docker('inspect', name).stdout)[0]['State']
        if not state['Running']:
            raise RuntimeError(docker('logs', name).stdout)
        if state['Health']['Status'] == 'healthy':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Mobile did not become healthy')
    logs = docker('logs', name).stdout
    assert 'uiautomator2@8.7.2' in logs, logs
    # Losing a child must stop the whole container, not silently restart ADB.
    docker('exec', name, 'adb', 'kill-server')
    for _ in range(30):
        state = json.loads(docker('inspect', name).stdout)[0]['State']
        if not state['Running']:
            assert state['ExitCode'] != 0
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Container survived ADB failure')
    print('Mobile smoke test passed: servers, driver, read-only/non-root, fail-fast')
finally:
    docker('rm', '-f', name, check=False)
