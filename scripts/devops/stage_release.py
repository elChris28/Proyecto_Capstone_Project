"""Prepara y activa versión incremental en staging LOCAL/EFÍMERO.

Cada versión queda en releases/<release-id> y se activa solamente si pasa
un chequeo Flask /health desde la propia copia publicada. No configura
servidores, DNS, HTTPS ni despliegue productivo remoto.

Uso: python -m scripts.devops.stage_release --target build/staging --release-id sprint2-local-01
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = ('app', 'data', 'models', 'scripts')
FILES = ('config.py', 'main.py', 'requirements.txt', 'requirements-dev.txt')


def _ignore(_dir, names):
    return {n for n in names if n in ('__pycache__','.pytest_cache','.git','.venv','.env','build')
            or n.endswith(('.pyc','.pyo'))}


def stage(target: Path, release_id: str, *, smoke: bool=True) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{2,63}',release_id):
        raise ValueError('release-id inválido: utilizar 3-64 letras, números, puntos, guiones o guion bajo')
    target = target.resolve()
    source = ROOT.resolve()
    if target == source or source in target.parents and target.name in DIRECTORIES:
        raise ValueError('No se permite sobrescribir carpetas fuente del proyecto')
    releases = target / 'releases'
    releases.mkdir(parents=True,exist_ok=True)
    final = releases / release_id
    if final.exists():
        raise FileExistsError(f'La versión ya está preparada: {release_id}')
    temporary = releases / ('.preparando-' + uuid.uuid4().hex)
    temporary.mkdir()
    try:
        for name in DIRECTORIES:
            shutil.copytree(source/name, temporary/name, ignore=_ignore)
        for name in FILES:
            shutil.copy2(source/name, temporary/name)
        if smoke:
            python_cmd=(
                "from app import create_app; "
                "c=create_app().test_client(); "
                "r=c.get('/health'); "
                "assert r.status_code==200 and r.json.get('estado')=='activo', "
                "f'Health incorrecto: {r.status_code}'; "
                "print('STAGING_HEALTH_OK')"
            )
            env=os.environ.copy()
            env['APP_ENV']='development'
            # No se trasladan secretos del entorno local a la prueba empaquetada.
            for secret in ('DB_PASSWORD','SECRET_KEY','ADMIN_PASSWORD_HASH'):
                env.pop(secret,None)
            check=subprocess.run([sys.executable,'-c',python_cmd],cwd=temporary,
                                 env=env,capture_output=True,text=True,timeout=90)
            if check.returncode:
                raise RuntimeError('Health check staging falló:\n'+check.stderr[-2500:])
        temporary.rename(final)
        status='ACTIVADO' if smoke else 'PREPARADO_SIN_ACTIVAR'
        if smoke:
            pointer=target/'CURRENT.json'
            pointer_tmp=target/'.CURRENT.tmp'
            pointer_tmp.write_text(json.dumps({'release_id':release_id,
                              'modo':'staging_local_efimero','health':'OK'},indent=2)+'\n',encoding='utf-8')
            os.replace(pointer_tmp,pointer)
        return {'release_id':release_id,'estado':status,
                'destino':str(final),'health':'OK' if smoke else 'NO_EJECUTADO',
                'nota':'No es un despliegue productivo accesible por Internet.'}
    except Exception:
        shutil.rmtree(temporary,ignore_errors=True)
        raise


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=ROOT/'build'/'staging')
    parser.add_argument('--release-id',required=True)
    parser.add_argument('--no-smoke',action='store_true',help='Solo empaqueta; NO activa versión')
    args=parser.parse_args()
    try:
        print(json.dumps(stage(args.target,args.release_id,smoke=not args.no_smoke),indent=2,ensure_ascii=False))
        return 0
    except (ValueError,FileExistsError,RuntimeError,subprocess.TimeoutExpired) as e:
        print(f'ERROR stage: {e}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
