# Set pi up for Blastoff

This setup uses repo context, workflow skills and prompts. It needs no custom
extension, model change, provider change, global skill installation or service.
The instructions are guidance for the agent; they are not filesystem isolation
or an enforced permission boundary. Continue using isolated tests.

## 1. Continue in the current checkout

The shared-core rebuild is already integrated in
`/data/data/com.termux/files/home/repos/blastoff`. Read VERSION, Git status,
AGENTS.md, CLI-CONTRACT.md, IMPLEMENTATION-PLAN.md and STATUS.md before work.
Do not repeat the historical 0.1.0 archive integration. Supplied/downloaded archives
remain review sources, never permission to overwrite the checkout.

## 2. Start pi and choose an accepted slice

```sh
cd /data/data/com.termux/files/home/repos/blastoff
pi
```

Ask it to continue the accepted incomplete slice, preserve unrelated work and
reference assets, use temporary test roots, and reconcile code/help/completions/
manual/docs. Record unrun native/human gates explicitly. No live installation,
profile/config changes or Git publication is implied. Final package/checksum
regeneration follows final edits. Existing skills/prompts below remain guidance,
not permission or filesystem isolation. Historical package-audit evidence remains
in SOURCE-AUDIT.md and TERMUX-AUDIT.md.

## 3. Project files pi can use

| File | Role |
|---|---|
| `AGENTS.md` | Always-relevant project priorities, paths, safety and verification |
| `docs/PROGRAMMING-PREFERENCES.md` | Reusable explicit preferences plus labeled inferences |
| `.pi/settings.json` | Relative project resource directories, skill commands enabled |
| `.pi/skills/blastoff-plan/SKILL.md` | Audit and plan a bounded implementation slice |
| `.pi/skills/blastoff-safe-config/SKILL.md` | Implement/review config, backup and module mutations |
| `.pi/skills/blastoff-parity/SKILL.md` | Keep wrappers, output and shell completion aligned |
| `.pi/skills/blastoff-release/SKILL.md` | Verify versioned lifecycle and release readiness |
| `.pi/prompts/plan.md` | `/plan [task]` — a planning workflow, not a built-in sandbox mode |
| `.pi/prompts/implement.md` | `/implement [slice]` — implement an accepted slice |
| `.pi/prompts/review.md` | `/review [focus]` — review changes against the contract |
| `.pi/prompts/checkpoint.md` | `/checkpoint` — record state, evidence and next steps |

After integrating these project files, reload pi resources in the active session
with `/reload`. Invoke a specific skill when needed:

```text
/skill:blastoff-plan plan the next bounded change
/skill:blastoff-safe-config review module-load failure behavior
/skill:blastoff-parity validate native Termux completions
/skill:blastoff-release check readiness without installing
```

Pi advertises skill metadata and loads the body when relevant; descriptions
must be specific. `/skill:name` forces loading. Prompt Markdown filenames become
slash commands. Project resource loading may require project trust in your pi
version. Inspect the files before granting trust. These resources were checked
against official pi docs on 2026-09-30; pi itself was not available for a live
startup/reload check here. Confirm discovery in your installed version.

## 4. Good everyday workflow

Use `/plan` for a new behavior or risky file change; inspect its concrete
acceptance cases. Use `/implement` for the selected slice, then `/review`.
Use `/checkpoint` before pausing or changing models/sessions. Keep the checkpoint
in docs, with exact test commands and unchecked host gates.

The prompts already tell pi to continue authorized reversible work. They do
not require repetitive approval for routine edits. Explicitly authorize a real
install, live-config change, commit/push or release when you want that action.
Do not add third-party agent extensions until a specific need justifies them.

## Official references

- Skills: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md
- Prompt templates: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/prompt-templates.md
- Settings: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md
- Pi home: https://pi.dev/

These URLs may redirect as the upstream repository changes. Prefer the docs
bundled with your installed pi version when behavior differs.

## 0.1.8 follow-up

The 0.1.8 workflow requires fancy-default/explicit --fzf browsers, bat inheritance,
human output by default and explicit JSON. Root PowerShell lifecycle and startup
checks are in POWERSHELL.md. Preserve the paused step-5 review and distinguish
fixtures, native platform runs and human appearance. Never infer installation.
