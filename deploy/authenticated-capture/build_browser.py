"""Build the pinned, narrowly patched browser and select its immutable local ID."""
from pathlib import Path
import os
import re
import subprocess


def build(root):
    root = Path(root).resolve()
    kit = root / 'deploy' / 'authenticated-capture'
    env = root / '.local' / 'authenticated-capture' / '.env'
    if not env.exists():
        raise RuntimeError('Run prepare.py before building the browser')
    tag = 'transcriptlens/vexa-bot-auth:v0.12.28-1'
    subprocess.run(['docker', 'build', '--network=none', '--pull=false',
                    '-t', tag, '-f', str(kit / 'Dockerfile.bot'), str(kit)], check=True)
    image = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', tag],
                           capture_output=True, text=True, check=True, timeout=20).stdout.strip()
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise RuntimeError('The built browser has no immutable image ID')
    lines = [line for line in env.read_text().splitlines() if not line.startswith('AUTH_BOT_IMAGE=')]
    lines.append('AUTH_BOT_IMAGE=' + image)
    os.umask(0o077)
    temporary = env.with_suffix('.build.tmp')
    with temporary.open('x', encoding='utf-8') as output:
        output.write('\n'.join(lines) + '\n')
    temporary.replace(env)
    print('Authenticated browser built and pinned by local image ID. No meeting was joined.')


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[2])
