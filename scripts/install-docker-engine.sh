#!/usr/bin/env bash
# Replace Docker Snap with official Docker Engine on Ubuntu.
# Run: sudo bash scripts/install-docker-engine.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo 'Run with sudo bash scripts/install-docker-engine.sh' >&2
  exit 1
fi

source /etc/os-release
if [[ ${ID:-} != ubuntu ]]; then
  echo 'This script supports Ubuntu only.' >&2
  exit 1
fi
codename=${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}
if [[ -z $codename ]]; then
  echo 'Cannot determine Ubuntu codename.' >&2
  exit 1
fi
login_user=${SUDO_USER:-}
if [[ -z $login_user || $login_user == root ]]; then
  echo 'Run using sudo from your normal user account.' >&2
  exit 1
fi
id "$login_user" >/dev/null

echo 'This installs Docker Engine and replaces conflicting Engine packages.'
echo 'Project files and bind-mounted data directories will not be deleted.'
read -r -p 'Continue? [y/N] ' answer
case "$answer" in y|Y) ;; *) exit 0 ;; esac

conflicts=()
for package in docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc; do
  if [[ $(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true) == 'install ok installed' ]]; then
    conflicts+=("$package")
  fi
done
# Keep apt's interactive confirmation so dependency removals can be reviewed.
if (( ${#conflicts[@]} )); then
  apt-get remove "${conflicts[@]}"
fi

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$codename" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker "$login_user"
/usr/bin/docker version
/usr/bin/docker compose version

echo 'Installation complete. Log out and back in to activate Docker group membership.'
echo 'Warning: membership of the docker group grants root-equivalent access.'
echo 'Then build the images: docker compose build'
