# Training your own text model (LoRA)

A LoRA fine-tune teaches a Qwen model a writing style or format, for example the scene-plan JSON this studio asks for.
Train on a rented GPU, not a phone (a phone has no GPU and too little RAM).
**Status: template, untested.** It was written without being run; expect to fix version issues.

## Requirements
- NVIDIA GPU, 16-24 GB VRAM for a 7-9B model with 4-bit LoRA (or rent one: RunPod, Vast.ai, Colab Pro).
- Python 3.10+, `pip install unsloth trl datasets` (see https://docs.unsloth.ai for current install steps).

## Dataset rules
- Only content you have the right to use, between adult characters. No minors, no real people, no non-consensual content involving real persons. Remove anything that violates this before training.
- Format: JSONL, one conversation per line:
  `{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`
- Quality beats size: a few thousand clean, well-written examples is a decent start.
- Check each dataset's licence on Hugging Face before using it.

## Run
```
python training/train_lora.py --base Qwen/Qwen3.5-9B --data data/train.jsonl --out out/lora
```
Then merge + quantize with llama.cpp (`convert_hf_to_gguf.py`, then `llama-quantize ... Q4_K_M`), and load with Ollama using a Modelfile (`FROM ./your-model.Q4_K_M.gguf`).
If you publish the result, include a README with usage notes, the base model's licence and tags.
