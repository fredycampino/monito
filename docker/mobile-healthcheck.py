"""Health does not require a connected or authorized phone."""
import json
import socket
import urllib.request

with urllib.request.urlopen('http://127.0.0.1:4723/status', timeout=3) as response:
    if not json.load(response)['value']['ready']:
        raise SystemExit(1)
# Query the existing daemon directly: never start a replacement in a healthcheck.
with socket.create_connection(('127.0.0.1', 5037), timeout=3) as connection:
    connection.sendall(b'000chost:version')
    if connection.recv(4) != b'OKAY':
        raise SystemExit(1)
