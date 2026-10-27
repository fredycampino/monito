from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_mobile_is_optional_and_not_exposed():
    base = yaml.safe_load((ROOT / 'compose.yaml').read_text())
    override = yaml.safe_load((ROOT / 'docker/compose.mobile.yaml').read_text())
    assert 'mobile' not in base['services']
    server = override['services']['mobile']
    assert 'ports' not in server
    assert not server.get('privileged', False)
    assert server['cap_drop'] == ['ALL']
    assert server['device_cgroup_rules'] == ['c 189:* rw']
    assert override['networks']['mobile']['internal'] is True
    assert server['networks'] == ['mobile']
    assert override['services']['monito']['environment']['ADB_SERVER_SOCKET'] == 'tcp:mobile:5037'
    mounts = {mount['target']: mount for mount in server['volumes']}
    assert mounts['/data/home']['bind']['create_host_path'] is False
    assert mounts['/dev/bus/usb']['source'] == '/dev/bus/usb'
    assert '/dev/bus/usb' not in str(base['services']['monito']['volumes'])


def test_mobile_image_and_client_configuration():
    override = yaml.safe_load((ROOT / 'docker/compose.mobile.yaml').read_text())
    monito = override['services']['monito']
    assert monito['environment']['APPIUM_URL'] == 'http://mobile:4723'
    assert monito['depends_on']['mobile']['condition'] == 'service_healthy'
    server = override['services']['mobile']
    assert server['build']['dockerfile'] == 'docker/Dockerfile.mobile'
    assert server['read_only'] is True
    assert server['image'].startswith('${IMAGE_PREFIX:-}monito-mobile:')
    assert not (ROOT / 'docker/compose.adb.yaml').exists()
    mobile = (ROOT / 'docker/Dockerfile.mobile').read_text()
    assert 'npm ci' in mobile
    assert 'openjdk-17-jre-headless' in mobile
    assert 'sdkmanager' not in mobile
    client = (ROOT / 'docker/Dockerfile.monito').read_text()
    assert 'install -y --no-install-recommends adb' in client
    assert 'adb-server' not in client
