# Text-to-Movie Studio

Turn a story idea into a short film: **text in, MP4 with video and audio out.**

```
idea ──► scene writer (LLM) ──► plan.json ──► video backend ──► clips ──► ffmpeg ──► movie.mp4
          Ollama / OpenAI-API     you can       ComfyUI (any       one per     joined, same
          or none                 edit it       model you pick)    scene       size/fps/audio
```

- The **scene writer** asks a language model for a title, a cast (every character an adult, with an age) and a
  list of scenes (setting, action, spoken line, sound, camera, length).
- Each scene becomes one descriptive prompt and is rendered by a **video backend**. Scene N's last frame is fed
  to scene N+1 as its first frame, when the backend supports it, so the film stays continuous.
- **ffmpeg** normalises the clips and joins them. The final file is checked to have both a video and an audio stream.
- Everything is saved in a run folder (`runs/<time>-<slug>/`), so a failed run **resumes** instead of starting over.
- Standard library only. No `pip install` needed beyond the package itself.

## Status: read this first

| Part | State |
|---|---|
| Scene writer, guard, plan parsing, stitching, CLI | Tested on Android/Termux only (26 tests + `selftest`). Linux, macOS and Windows are **not yet verified**; `ci/github-actions-ci.yml` is ready to enable |
| Mock backend (colour card + tone) | Tested end to end, final MP4 has H.264 video and AAC audio |
| ComfyUI backend | Tested against a **fake** ComfyUI server only. **Never run against a real model.** |
| Ollama / OpenAI-compatible writer | Tested against fake servers only |
| `scripts/gpu_setup.sh` | Untested template |

**No video model is included and none is the default.** The default backend is `mock`, which only proves the
plumbing works. You choose and install the model (see "Pick a model" below).

## Install and run (any device)

Full guide for Linux, macOS, Windows and Termux: **[`docs/INSTALL.md`](docs/INSTALL.md)**. The short version:

```bash
gh auth login                       # the repo is private; choose HTTPS
git clone https://github.com/MADavisFS20/text-to-movie-studio.git
cd text-to-movie-studio
bash scripts/install.sh             # Windows: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
python3 -m movie_studio make "$(cat examples/idea.txt)" --writer template --scenes 3
```
You need Python 3.9+ and ffmpeg. The installer checks both, then renders a tiny mock movie and fails unless the
MP4 has video **and** audio. The movie lands in `runs/<time>-<slug>/movie.mp4` (coloured clips with a tone per
scene: it proves the pipeline works, it is not real video). Real video needs a GPU and a licensed model, see below.

## Commands

| Command | What it does |
|---|---|
| `plan "idea"` | Write `plan.json` only. Edit it by hand, then render. |
| `render RUN_DIR` | Render a run's `plan.json` into `movie.mp4`. Reuses clips that already exist. |
| `make "idea"` | Plan and render in one go. |
| `doctor` | Check ffmpeg and your config. |

Flags: `--config FILE`, `--writer {ollama,openai,template,file}`, `--backend {mock,comfyui}`, `--scenes N`,
`--runs DIR`, `--out DIR`, `--plan-file FILE` (with `--writer file`).

Exit codes: `0` ok, `2` error, `3` refused by the content guard.

## Real video: ComfyUI on a rented GPU

Video models need a big GPU. A phone cannot run one. Rent a GPU box (any provider whose terms allow your
content), run ComfyUI there, and drive it from anywhere.

1. **GPU box:** run `scripts/gpu_setup.sh` (read it first), install your chosen model's files as its README says,
   and start ComfyUI bound to localhost: `python main.py --listen 127.0.0.1 --port 8188`.
2. **Tunnel:** `ssh -N -L 8188:127.0.0.1:8188 USER@GPU_HOST`. Do not expose ComfyUI to the internet.
3. **Workflow:** build a text-to-video+audio workflow in ComfyUI and export it with *Save (API Format)* to
   `workflows/workflow_api.json`. Map its inputs in your config. Full steps: [`workflows/README.md`](workflows/README.md).
4. **Config:** `cp config.example.json config.json` and edit the node ids.
5. **Check and run:**
   ```bash
   python3 -m movie_studio doctor --config config.json
   python3 -m movie_studio make "$(cat examples/idea.txt)" --config config.json
   ```

If your first clip comes back wrong, run one scene at a time with `plan` then `render`, and compare the
prompt in `plan.json` with what your model expects. Different models like different prompt styles; the
`video.style` setting appends your own style words to every scene.

## Scene writer options

| `writer.provider` | Needs |
|---|---|
| `ollama` | An Ollama server (`writer.url`, `writer.model`). Uses `/api/chat` with JSON output. |
| `openai` | Any OpenAI-compatible server and optional `writer.api_key`. Uses `/v1/chat/completions`. |
| `template` | Nothing. Splits your idea into scenes with no LLM. For testing. |
| `file` | You write `plan.json` yourself and pass `--plan-file`. |

Small models often break JSON, so the writer retries up to 3 times. **On a low-RAM phone, do not run the model
on the phone**: point `writer.url` at a bigger machine, or use `template`/`file`. Loading a model next to other
apps is enough to get the process killed.

## Pick a model: licences matter

This tool does not give you any right to use a model. **You must check the licence of the model you run, and of
the base model underneath any fine-tune.** Things to check: commercial use, revenue limits, attribution, and
**territory**.

Example of why this matters: MiniMax H3's Community License, as published, defines "Excluded Territories" as
the European Union, the United Kingdom, the Republic of Korea and the United States (Section I.5), and its grant
(Section II) applies only outside them. Fine-tunes of H3 inherit that, whatever licence tag the fine-tune carries.
Read the licence text yourself; this README is not legal advice.

If you plan to charge for outputs or run this for other people, also read your GPU host's and payment
provider's acceptable-use terms, and the model licence's rules for hosted services.

## Safety (built in, on by default)

- **Adults only.** Every character needs an integer age of 18 or more (the writer prompt asks for 21+). The guard
  refuses minors and youthful-coded terms, stated ages under 18, and school-age settings. It runs on your idea,
  on the model's output, and again on the exact prompt sent to the renderer, including hand-edited plans.
- **Fictional characters only.** Requests for a real person's likeness or a face swap are refused.
- **Image input is off.** `--first-frame` works only if `safety.allow_image_input` is `true` **and** you pass
  `--confirm-fictional-subject`. Continuity frames come from the pipeline's own previous clip, not from you.
- Refusal messages quote at most the single flagged word, never your whole text.

**What this is not:** the guard is a keyword and number check. It will miss things and can reject harmless text.
It is not a moderation system. If you let other people use this, you need a real moderation model, request
logging, human review, a way for people to report problems, age verification where the law requires it, and
your own legal advice. That work is not included.

## Content and GitHub

Do not commit generated videos or adult material to this repo or any public GitHub repo: GitHub's terms
prohibit sexually explicit content. `runs/`, `config.json` and `workflows/*.json` are git-ignored.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```
Needs `ffmpeg` and `ffprobe`; tests that render are skipped without them. No network and no GPU needed.

## Layout

```
movie_studio/
  guard.py       content guard
  scenes.py      plan model, JSON parsing, prompt composition
  writer.py      Ollama / OpenAI-compatible / template / file
  backends/      mock.py, comfyui.py (add your own: subclass Backend)
  stitch.py      ffprobe / last frame / normalise / concat
  pipeline.py    plan -> render -> movie
  cli.py
tests/  workflows/  scripts/  examples/  docs/  models/  training/  ci/
```

To add a backend, subclass `Backend`, implement `render(scene, out_path, first_frame)` so it writes an MP4 with
video and audio, and register it in `backends/__init__.py`.

## License

MIT for this code. Models you use have their own licences.
