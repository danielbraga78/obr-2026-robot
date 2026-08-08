#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source .venv/bin/activate

echo "Testando câmera com OpenCV..."
python - <<'PY'
import cv2
import sys

for index in range(0, 5):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        print(f"Câmera encontrada no dispositivo {index}")
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"Frame lido com sucesso: shape={frame.shape}")
        else:
            print(f"Falha ao ler frame do dispositivo {index}")
        cap.release()
        sys.exit(0)
    cap.release()

print("Nenhuma câmera foi detectada nos dispositivos 0..4")
sys.exit(1)
PY
