#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source .venv/bin/activate

echo "Testando câmera..."
python - <<'PY'
import sys

from raspberry.camera import CameraManager

camera = CameraManager(backend="auto")
try:
    frame = camera.read_frame()
    if frame is None:
        print(f"Câmera abriu, mas não entregou frame: {camera.describe()}")
        sys.exit(1)
    print(f"Frame lido com sucesso: backend={camera.describe()} shape={frame.shape}")
finally:
    camera.release()
PY
