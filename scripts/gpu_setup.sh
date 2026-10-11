#!/usr/bin/env bash
# Sets up ComfyUI on a rented Linux GPU box (NVIDIA, CUDA drivers already installed).
# UNTESTED template: read it before running, and check ComfyUI's README for your GPU/torch combination.
# It does NOT download any model. Pick a model whose licence allows your use (see the main README).
set -euo pipefail

DIR="${1:-$HOME/ComfyUI}"
[ -d "$DIR" ] || git clone https://github.com/comfyanonymous/ComfyUI.git "$DIR"
cd "$DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
# Install the torch build that matches your CUDA version first; see https://pytorch.org/get-started/locally/
pip install torch torchvision torchaudio
pip install -r requirements.txt

cat <<MSG

ComfyUI is installed in $DIR.
Next:
  1. Put your model files under $DIR/models/ as that model's instructions say.
  2. Start it bound to localhost only (do not expose it to the internet):
       cd $DIR && . .venv/bin/activate && python main.py --listen 127.0.0.1 --port 8188
  3. From your phone/PC, tunnel the port:
       ssh -N -L 8188:127.0.0.1:8188 USER@GPU_HOST
  4. Point comfyui.url at http://127.0.0.1:8188 and run: python3 -m movie_studio doctor --config config.json
MSG
