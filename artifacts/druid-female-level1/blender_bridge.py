"""Send an explicitly supplied Python script to the local Blender Lab bridge."""
import argparse
import json
import socket
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('script')
parser.add_argument('--timeout', type=int, default=180)
args = parser.parse_args()
request = {'type': 'execute', 'strict_json': False, 'code': Path(args.script).read_text(encoding='utf-8')}
with socket.create_connection(('localhost', 9876), timeout=10) as connection:
    connection.settimeout(args.timeout)
    connection.sendall(json.dumps(request).encode() + b'\0')
    chunks = bytearray()
    while b'\0' not in chunks:
        block = connection.recv(65536)
        if not block:
            break
        chunks.extend(block)
response = json.loads(chunks.split(b'\0')[0])
print(json.dumps(response, indent=2))
if response.get('status') != 'ok':
    raise SystemExit(1)
