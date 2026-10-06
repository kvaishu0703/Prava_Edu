"""One-command local setup. Run START-PRAVA.cmd on Windows, or python launch.py."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='Prepare and start the local PRAVA college portal.')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--without-demo', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise RuntimeError('Choose a port between 1024 and 65535.')
    url = f'http://127.0.0.1:{args.port}'
    instance_id = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    if not args.prepare_only:
        with socket.socket() as check:
            occupied = check.connect_ex(('127.0.0.1', args.port)) == 0
        if occupied:
            try:
                with urlopen(url+'/health', timeout=3) as response:
                    health = json.load(response)
                if health.get('local_instance') == instance_id:
                    if health.get('demo_mode') != (not args.without_demo):
                        raise RuntimeError('The running PRAVA server uses a different demo setting. Stop its server window with Ctrl+C, then run this command again.')
                    print(f'PRAVA is already running: {url}', flush=True)
                    if not args.no_browser:
                        webbrowser.open(url)
                    return 0
            except RuntimeError:
                raise
            except Exception:
                pass
            raise RuntimeError(f'Port {args.port} is in use. Close the previous local server or run Start-PRAVA.ps1 -Port {args.port + 1}.')
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise RuntimeError('Use Python 3.11, 3.12 (recommended), or 3.13. On Windows START-PRAVA.cmd selects it automatically.')
    os.chdir(ROOT)
    venv_dir = ROOT / '.venv'
    venv_python = venv_dir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if Path(sys.prefix).resolve() != venv_dir.resolve():
        if not venv_python.exists():
            print('Creating the project Python environment...', flush=True)
            subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
        return subprocess.call([str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT)

    instance = ROOT / 'instance'
    instance.mkdir(exist_ok=True)
    requirements = ROOT / 'requirements.txt'
    dependency_stamp = hashlib.sha256(requirements.read_bytes()+sys.version.encode()).hexdigest()
    marker = instance / '.dependencies-ready'
    if not marker.exists() or marker.read_text(encoding='utf8') != dependency_stamp:
        print('Installing project dependencies (internet is needed the first time)...', flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        marker.write_text(dependency_stamp, encoding='utf8')

    secret_path = instance / '.local-secret'
    if not secret_path.exists():
        try:
            with secret_path.open('x', encoding='utf8') as secret_file:
                secret_file.write(secrets.token_urlsafe(48))
        except FileExistsError:
            pass
    os.environ.update(FLASK_ENV='development', SUPABASE_AUTH_ENABLED='false',
                      PRAVA_DEMO_MODE='false' if args.without_demo else 'true',
                      SECRET_KEY=secret_path.read_text(encoding='utf8'),
                      DATABASE_URL='sqlite:///'+(instance/'prava.sqlite3').as_posix(),
                      PRAVA_LOCAL_INSTANCE=instance_id)
    database = instance / 'prava.sqlite3'
    if not args.without_demo:
        from project_data import restore_project_data
        if restore_project_data(ROOT):
            print('Loaded the complete project data and uploaded files. Private login details: instance/PRAVA_Local_Login_Details.txt (also CSV for Excel)', flush=True)
    schema_files = [ROOT/'app/__init__.py', *sorted((ROOT/'app/models').glob('*.py'))]
    schema_stamp = hashlib.sha256(b''.join(p.read_bytes() for p in schema_files)).hexdigest()
    schema_marker = instance / '.schema-ready'
    if database.exists() and (not schema_marker.exists() or schema_marker.read_text(encoding='utf8') != schema_stamp):
        backups = instance / 'backups'
        backups.mkdir(exist_ok=True)
        backup = backups / (datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-before-upgrade.sqlite3')
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)
        print(f'Database backup saved: {backup.name}', flush=True)

    from app import create_app
    app = create_app('development')
    runner = app.test_cli_runner()
    for command in ['upgrade-db', 'sync-college', *([] if args.without_demo else ['setup-demo'])]:
        result = runner.invoke(args=[command])
        print(result.output.strip(), flush=True)
        if result.exit_code:
            raise RuntimeError(f'{command} failed: {result.exception}')
    schema_marker.write_text(schema_stamp, encoding='utf8')
    if args.prepare_only:
        print('PRAVA setup complete. Database and accounts persist between runs.', flush=True)
        return 0
    from werkzeug.serving import make_server
    server = make_server('127.0.0.1', args.port, app, threaded=True)
    login_note = ('Private login details: instance/PRAVA_Local_Login_Details.txt (also CSV for Excel)'
                  if (instance/'PRAVA_Local_Login_Details.txt').exists()
                  else 'Use your existing login passwords or the project owner\'s private handout.')
    print(f'\nPRAVA is ready: {url}\nKeep this window open. Press Ctrl+C to stop.\n{login_note} | Instructions: README.md', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nPRAVA stopped. Your data is saved.', flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'\nSetup could not finish: {error}', file=sys.stderr, flush=True)
        sys.exit(1)
