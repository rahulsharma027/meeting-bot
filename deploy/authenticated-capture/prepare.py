"""Prepare local secrets and a verified upstream storage initializer. No capture."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import urllib.request

REVISION = 'f1a62fbbdfd2c98cb162582d82c31fe8102acc89'
INITIALIZER_SHA256 = '394f61caa96dd202e11da51192792d51848391f516dadbd840623554a02da5c3'


def prepare(root):
    root = Path(root).resolve()
    os.umask(0o077)
    data = root / '.local' / 'authenticated-capture'
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    initializer = data / 'storage_init.py'
    if initializer.exists():
        body = initializer.read_bytes()
    else:
        url = f'https://raw.githubusercontent.com/Vexa-ai/vexa/{REVISION}/deploy/storage/storage_init.py'
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read(100_001)
    if hashlib.sha256(body).hexdigest() != INITIALIZER_SHA256:
        raise RuntimeError('Upstream storage initializer failed digest verification')
    if not initializer.exists():
        with initializer.open('xb') as output:
            output.write(body)
    env = data / '.env'
    if not env.exists():
        values = {name: secrets.token_hex(32) for name in (
            'DB_PASSWORD', 'ADMIN_TOKEN', 'INTERNAL_API_SECRET',
            'STORAGE_ACCESS_KEY', 'STORAGE_SECRET_KEY',
            'USERDATA_ACCESS_KEY', 'USERDATA_SECRET_KEY',
        )}
        values['STORAGE_INIT_SCRIPT'] = json.dumps(initializer.as_posix())
        with env.open('x', encoding='utf-8') as output:
            output.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    print('Private configuration is ready; existing secrets were preserved. No meeting was joined.')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[2])
