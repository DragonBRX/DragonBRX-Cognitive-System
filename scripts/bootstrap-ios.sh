#!/bin/sh
set -eu

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 não está disponível. Instale o a-Shell completo." >&2
  exit 1
fi

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

echo "DragonBRX iOS: dependências externas necessárias = 0"
echo "Validando os módulos locais..."
python3 -m py_compile \
  src/distributed_runtime.py \
  src/pairing.py \
  src/ios_worker.py \
  src/ios_bootstrap.py

exec python3 src/ios_bootstrap.py "$@"
