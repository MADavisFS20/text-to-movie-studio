# Candidate models (found on Hugging Face via search, 2026-10-08; check each model card and licence before use)

Abliterated = refusal behaviour removed from an existing Qwen. Not the same as being trained on adult writing; for better prose, look for "roleplay"/"creative" fine-tunes or train your own (FINETUNE.md).

## Small (phone / 8 GB machines)
- https://hf.co/mradermacher/Qwen3.5-2B-uncensored-ara-GGUF  (2B; Q4_K_M 1.27 GB) - used in this repo
- https://hf.co/mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF  (4B; Q4_K_M 2.5 GB) - used in this repo
- https://hf.co/mradermacher/Huihui-Qwen3.5-4B-abliterated-GGUF

## Mid (16 GB RAM or 8-12 GB VRAM)
- https://hf.co/mradermacher/Huihui-Qwen3.5-9B-abliterated-GGUF
- https://hf.co/DavidAU/Qwen3.5-9B-The-Defiant-Fable-Uncensored-Heretic-NEO-IMATRIX-MAX-MTP-GGUF  (creative/roleplay tuned)

## Large (16-24 GB VRAM or 32 GB+ unified memory)
- https://hf.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF
- https://hf.co/JonathanColetti/Qwen3.8-27B-Uncensored-GGUF
- https://hf.co/bartowski/orcarouter_Qwen3.8-27B-Uncensored-GGUF
- https://hf.co/DavidAU/Qwen3.6-27B-Heretic-Uncensored-FINETUNE-NEO-CODE-Di-IMatrix-MAX-GGUF  (fiction/romance tags)
- https://hf.co/mradermacher/Huihui-Qwen3.6-35B-A3B-abliterated-GGUF  (MoE: 35B total, ~3B active, so fast on CPU+RAM if you have 24 GB+)

Quant guide: Q4_K_M = default; Q5_K_M if you have spare memory; Q3_K_M / IQ3 only if it won't fit; Q2 degrades a lot.
Some of these are multimodal/MTP builds; if Ollama or llama.cpp rejects one, pick a plain text GGUF from mradermacher or bartowski instead.
