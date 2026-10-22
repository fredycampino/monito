from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_adb_is_optional_and_not_exposed():
    base = yaml.safe_load((ROOT / 'compose.yaml').read_text())
    override = yaml.safe_load((ROOT / 'docker/compose.adb.yaml').read_text())
    assert 'adb' not in base['services']
    server = override['services']['adb']
    assert 'ports' not in server
    assert not server.get('privileged', False)
    assert server['cap_drop'] == ['ALL']
    assert server['device_cgroup_rules'] == ['c 189:* rw']
    assert override['networks']['adb']['internal'] is True
    assert server['networks'] == ['adb']
    assert override['services']['monito']['environment']['ADB_SERVER_SOCKET'] == 'tcp:adb:5037'
    mounts = {mount['target']: mount for mount in server['volumes']}
    assert mounts['/data/home']['bind']['create_host_path'] is False
    assert mounts['/dev/bus/usb']['source'] == '/dev/bus/usb'
    assert '/dev/bus/usb' not in str(base['services']['monito']['volumes'])


def test_adb_client_and_server_share_installation():
    dockerfile = (ROOT / 'docker/Dockerfile.monito').read_text()
    assert 'FROM adb-base AS adb-server' in dockerfile
    assert 'FROM adb-base AS monito' in dockerfile
    assert 'ENV HOME=/data/home' in dockerfile
    assert '"server", "nodaemon"' in dockerfile
