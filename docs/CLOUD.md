# Running the pipeline in Claude Code cloud sessions

The processing of the public-domain run (volumes 1–59, about 14 million words)
is meant to run in Claude Code cloud sessions, not on the local machine. Cloud
sessions draw on the Claude plan's usage allowance. There is no separate budget
to configure per project.

## One-time setup

1. **Push the repository to GitHub** (private is fine). Cloud sessions clone
   from GitHub, not from the local disk.
2. **Connect GitHub** at claude.ai/code and install the Claude GitHub App for
   this repository.
3. **Create a cloud environment** (for example `woodstock`):
   - **Network access: Custom.** Allow `archive.org` and `*.archive.org`, because
     downloads are served from data nodes such as `ia8xxxxx.us.archive.org`.
     Tick "also include default list" so that pip works.
   - **Setup script:** `bash tools/setup.sh` (installs `wordfreq`).
4. Test with one small volume first: fetch, build, open the QA report.

## Starting a session

- Desktop app: new session, choose **Cloud**, pick the `woodstock` environment.
- Terminal, inside the repository: `claude --cloud "Process vols. 30–34 per CLAUDE.md"`.
- A cloud session can be pulled back to the terminal with `claude --teleport <session-id>`.

Only committed and pushed work survives a cloud session. The pipeline is
idempotent. `data/raw/` is re-fetched, so each session starts clean, fetches,
builds, reviews, commits and pushes.

## Batch runs as a routine

For unattended progress, create a routine (claude.ai/code/routines, or `/schedule`
in the CLI) with this environment and a prompt such as:

> Read CLAUDE.md. Find the next five volumes in 1–59 that are not yet in
> data/manifest.json. Fetch and build them, review each QA report as CLAUDE.md
> describes, fix recurring heuristic failures, update docs/PROGRESS.md, commit,
> push to a branch `batch/<vols>`, and open a pull request. Stop and report
> instead of committing if a volume fails the pagination cross-check.

Work in pull requests so every batch is reviewed before it reaches the live site.

## Size

Per issue the pipeline downloads about 250 KB of OCR (no scans). Built volumes
come to roughly 1.5 MB of JSON each, so about 90 MB for the public-domain run.
That is fine for git and Netlify. Search will move to a Pagefind index before
the corpus gets that large.
