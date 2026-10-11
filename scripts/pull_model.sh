#!/usr/bin/env bash
# Pull a GGUF text model into Ollama and register it under a short name.
# usage: ./scripts/pull_model.sh [hf-repo] [quant] [name]
# default: the small Qwen 2B build that fits an 8 GB machine. Check the model's licence before use.
# Do NOT run a model on a low-RAM phone: it can get the whole terminal session killed.
set -e
repo=${1:-mradermacher/Qwen3.5-2B-uncensored-ara-GGUF}
quant=${2:-Q4_K_M}
name=${3:-qwen-2b-uncensored}
command -v ollama >/dev/null 2>&1 || { echo "Ollama is not installed: https://ollama.com/download"; exit 1; }
cd "$(dirname "$0")/.."
ollama pull "hf.co/$repo:$quant"
tmp=$(mktemp)
sed -e "s|__REPO__|$repo|" -e "s|__QUANT__|$quant|" models/Modelfile.template > "$tmp"
ollama create "$name" -f "$tmp"
rm -f "$tmp"
echo "Done. Test: ollama run $name"
echo "Then set writer.model to \"$name\" in config.json."
