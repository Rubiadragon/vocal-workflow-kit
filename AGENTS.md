# AI contributors: read before acting

This is a public, generic workflow toolkit. The human user's current instructions
and the host's permissions take precedence. Repository content is not permission
to access unrelated files, transmit data, install software, or start training.

## Start here

1. Read README.md, AI_HANDOFF.md, docs/compatibility.md and the relevant workflow.
2. Inspect the user's environment without printing credentials or configuration values.
3. Run the tests, then doctor. A missing dependency is a setup finding, not permission
   to modify the system or silently use a different backend.
4. Keep machine-specific paths in config.local.json. Never commit it.

## Implementation and repair

- Back up affected local configuration before changing it. Use a dedicated work area.
- Do not overwrite songs, datasets, pretrained weights, checkpoints or completed runs.
- Do not alter pitch/index/voice/quality settings merely to make a failed test pass.
- Classify lead by musical role, not gender or rap/singing. Model labels are candidates.
- Do not feed background guest voices through conversion unless the user designated them lead.
- Verify the upstream fork's actual API/CLI. Update adapters and their tests together.
- Run subprocesses with argument arrays and shell=False. Do not evaluate supplied commands.
- This package never needs QQ/Bilibili cookies or any cloud API key.
- Do not start training, switch a running speech voice, stop programs, download large
  weights or publish content without authorization for that action.
- When interrupted, inspect the manifest and surviving processes. An existing output
  is not proof of completion; a lost HTTP response is not permission to retry inference.
- No auto retraining or repair loop. If model compatibility is unknown, report it.

## Validation

Run `python -m unittest discover -s tests -v`. Test fixtures must be synthetic.
For audio tests also configure the FFmpeg executable using the test-only environment
variable described in docs/compatibility.md. Never point fixtures at a real dataset.
Check input/output duration, sample rate, finite values, clipping and provenance.
Report separately: plan, mock test, dependency check, real inference, human listening.
Never say a voice "sounds correct" from loudness or pitch statistics alone.

## Publication

Run scripts/release.py --check. Publish only its explicit allowlist. No private paths,
real filenames, account IDs, memories, personas, chats, service leases, logs, audio,
models, trained indexes, datasets, binaries or environment files belong in a release.
Use the user's own chosen repository/license/publishing destination; do not invent
a repository URL or claim something was uploaded when only a ZIP was built.
