# Install and run

Works on Linux, macOS, Windows and Termux (Android). The studio itself is plain Python (standard library
only) plus ffmpeg. Video models are a separate, optional, GPU-hungry part (section 5).

## 0. Get the code on a new device
The repo is private, so sign in first.

```bash
# easiest: GitHub CLI  (https://cli.github.com)
gh auth login                 # choose HTTPS
git clone https://github.com/MADavisFS20/text-to-movie-studio.git
cd text-to-movie-studio
```
Without the GitHub CLI, create a personal access token (GitHub > Settings > Developer settings, repo read
access) and use it as the password when `git clone` asks. Do not paste tokens into chat or commit them.

## 1. Install the two prerequisites
| | Python 3.9+ | ffmpeg (includes ffprobe) |
|---|---|---|
| Debian/Ubuntu | `sudo apt install python3` | `sudo apt install ffmpeg` |
| macOS | `brew install python` | `brew install ffmpeg` |
| Windows | `winget install Python.Python.3.12` | `winget install Gyan.FFmpeg` (then open a **new** terminal) |
| Termux | `pkg install python` | `pkg install ffmpeg git` |

## 2. Check it works (no GPU, no model needed)
```bash
bash scripts/install.sh            # Linux / macOS / Termux / WSL / Git Bash
```
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1      # Windows
```
It checks Python and ffmpeg, then renders a tiny mock movie and passes only if the MP4 has **video and audio**.
You can also run just the test: `python3 -m movie_studio selftest` (`python -m ...` on Windows).

Make a first movie (no language model, coloured placeholder clips):
```bash
python3 -m movie_studio make "$(cat examples/idea.txt)" --writer template --scenes 3
```
The result is `runs/<time>-<slug>/movie.mp4`.

## 3. Add a text model for the scene writer (optional)
The writer needs an LLM served by Ollama (or any OpenAI-compatible server).
1. Install Ollama: https://ollama.com/download
2. `bash scripts/pull_model.sh` (Windows: `scripts\pull_model.ps1`). Defaults to a small Qwen 2B build; pass your
   own repo/quant/name for something bigger, see [`MODELS.md`](MODELS.md). Check each model's licence.
3. `cp config.example.json config.json`, set `writer.model` to the name you registered, and run:
   `python3 -m movie_studio plan "your idea" --config config.json`

**Do not run an LLM on a phone with about 4 GB of RAM.** Loading a model there can get the whole session killed.
Run Ollama on a PC or server and set `writer.url` to it.

## 4. Optional: pip install
`pip install -e .` gives you a `movie-studio` command. It is not required; `python3 -m movie_studio` always works.

## 5. Real video: a GPU box plus a model you are licensed to use
The mock renderer proves the plumbing. Real clips need a video model, which needs a GPU with a lot of VRAM
(many need 24 GB or more). **No model is bundled.** Pick one whose licence covers your country and your use; some
open-weight video models exclude whole regions, and fine-tunes inherit their base model's terms. Read the licence.

1. Rent or own a Linux machine with an NVIDIA GPU. Run `scripts/gpu_setup.sh` there (read it first; it installs
   ComfyUI only) and put your model's files where that model says.
2. Start ComfyUI on localhost: `python main.py --listen 127.0.0.1 --port 8188`.
3. From the device where you use the studio, tunnel the port: `ssh -N -L 8188:127.0.0.1:8188 USER@GPU_HOST`.
4. Build a text-to-video+audio workflow in ComfyUI, export it with *Save (API Format)*, map its inputs.
   Step by step: [`../workflows/README.md`](../workflows/README.md).
5. `python3 -m movie_studio doctor --config config.json`, then `make ... --config config.json`.

This part has never been run against a real model by the author. Expect to adjust your workflow mapping.

## 6. Everything else in the repo
| Path | What |
|---|---|
| `movie_studio/` | The code |
| `tests/` | `python3 -m unittest discover -s tests -t .` |
| `models/Modelfile.template` | Ollama settings used by `pull_model` |
| `training/` | Optional LoRA fine-tune template for the text model (untested; needs a GPU) |
| `docs/MODELS.md` | Candidate text models (unverified list, check licences) |
| `ci/github-actions-ci.yml` | Ready-made CI (tests on Linux, macOS, Windows). Not active yet: move it to `.github/workflows/ci.yml` with a token that has the `workflow` scope (`gh auth refresh -s workflow`) |

Not in the repo, on purpose: model weights (huge, and licensed separately), your `config.json`, your exported
ComfyUI workflows, and anything you generate (`runs/`).

## Troubleshooting
- **`ffmpeg ... MISSING`**: install it (section 1). On Windows open a new terminal afterwards.
- **`/usr/bin/env: bad interpreter` on Termux**: run scripts with `bash scripts/install.sh`, not `./scripts/...`.
- **`REFUSED: ...` (exit 3)**: the content guard refused your text; every character must be an adult. See README, Safety.
- **`comfyui.inputs.prompt is required`**: your config has no input mapping yet; see `workflows/README.md`.
- **`this workflow is in the UI format`**: re-export with *Save (API Format)*.
- **Writer returns bad JSON**: small models do this. It retries 3 times; use a larger model or `--writer file`.
- **Render stops half way**: run `render RUN_DIR` again; finished clips are reused.
