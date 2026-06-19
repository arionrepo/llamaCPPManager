---
description: llamaCPPManager — rebuild the macOS menu-bar GUI and install it to /Applications (deterministic)
---

# /llamacpp-install-gui

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/.claude/commands/llamacpp-install-gui.md
**Description:** Repo-specific slash command for **llamaCPPManager** — rebuild the macOS menu-bar GUI and install it deterministically to /Applications. NOT generic — only applies to this repo.
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-06-19

---

## Scope

This command is **specific to the llamaCPPManager repo**:
`/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager`

It only makes sense when the current working repo is llamaCPPManager. Do not invoke from other repos. The command shells out to:

```
~/.local/bin/llamacpp-manager install-gui [flags]
```

which expects to find the llamaCPPManager Swift sources at the path baked into the CLI.

---

## Purpose

Run a single command to:

1. Detect whether a rebuild is needed (sources newer than built binary)
2. Build the Swift app if needed (`build_app.sh` with correct working directory)
3. Kill any running `llamaCPP Manager.app` instances
4. Replace `/Applications/llamaCPP Manager.app` with the freshly built bundle
5. Verify the installed binary's MD5 matches the build's MD5
6. Report the version (read from repo `VERSION` file)
7. Launch the new app and confirm the process is running

Exit code is propagated. Distinct codes per failure mode (0 ok, 2 build, 3 install, 4 launch, 5 MD5 mismatch).

## When to use

- After modifying anything under `gui-macos/Sources/` and you want to test in the actual app
- After a `/version-bump` to ship the new version
- When a user reports the GUI looks stale (likely running the previous build)
- As the last step after an `/execute-plan` that touched the GUI
- Any time you'd otherwise paste a 4-line `killall + rm + cp + open` sequence

## Why this exists

The shell pipeline `killall ... && rm -rf ... && cp -R ... && open ...` is brittle:
- Terminal newline wrapping breaks the spaced path `llamaCPP Manager.app`
- macOS file-handle release after `killall` is racy
- Old `/Applications` entry can shadow the new one if `rm` failed silently
- No verification that the binary actually got replaced
- No confirmation the launched process is the new one

`llamacpp-manager install-gui` handles all of these with proper sequencing, MD5 verification, and explicit error reporting via lifecycle events.

## How to invoke

### From Claude Code (this slash command)

Just say `/llamacpp-install-gui` in the chat. I will run:

```
~/.local/bin/llamacpp-manager install-gui
```

and report the result.

### From the agent autonomously (in `/execute-plan` or similar)

The agent should run the same CLI command — no special handling needed. The script is idempotent (skips reinstall if MD5s already match).

### Manually (terminal)

```bash
llamacpp-manager install-gui                # build (if needed) + install + launch
llamacpp-manager install-gui --no-launch    # install only
llamacpp-manager install-gui --no-rebuild   # use existing build/
llamacpp-manager install-gui --force        # always rebuild + reinstall
llamacpp-manager install-gui --quiet        # minimal output
```

Or call the underlying script directly:

```bash
/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/install_gui.sh
```

## Arguments

`$ARGUMENTS` (optional, passed verbatim to the CLI command): any combination of `--no-rebuild`, `--no-launch`, `--force`, `--quiet`.

## Execution

Run this exact bash command, streaming its output to the user:

```bash
~/.local/bin/llamacpp-manager install-gui $ARGUMENTS
```

After it completes:
- If exit code is 0 → confirm to the user: "GUI installed and launched (version from `VERSION` file)."
- If exit code is non-zero → show the last 10 lines of output and the exit code; suggest `llamacpp-manager lifecycle --tail 20` to inspect what happened.

Do **not** invent your own kill+rm+cp+open sequence. The CLI command is the single source of truth.

## Lifecycle events emitted

- `cli.install_gui.begin`   (with flags + script path)
- `cli.install_gui.result`  (with exit code)
- `cli.install_gui.interrupted` (if Ctrl-C)

Queryable later via:

```bash
llamacpp-manager lifecycle --tail 20
```

## Source of truth

- Shell script: `gui-macos/install_gui.sh`
- CLI wrapper: `src/llamacpp_manager/cli.py` → `cmd_install_gui`
- Slash command: this file
