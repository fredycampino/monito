#!/bin/sh
set -eu

skiller server start
exec "$@"
