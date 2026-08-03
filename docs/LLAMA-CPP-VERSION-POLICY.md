# llama.cpp Build / Version Policy

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/LLAMA-CPP-VERSION-POLICY.md
**Description:** Canonical policy for which llama.cpp build llamaCPPManager runs and how to prevent silent regression to an older/broken commit (resolves KNOWN-ISSUES I4).
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-08-03
**Last Updated:** 2026-08-03
**Last Updated By:** Claude (Opus 4.8)

## Why this exists

`llamaCPPManager` runs a single, locally-built `llama-server` for all GGUF
(native) models via the global `llama_server_path` in
`~/Library/Application Support/llamaCPPManager/config.yaml`. Because that build
directory is rebuilt in place from a moving git checkout, a routine
`git pull && cmake --build` can **silently swap the canonical binary to an
older or regressed commit** with no signal to the manager. That exact failure
caused the 2026-07-27 incident: a b8559 binary crashed on Mistral-Small-3.2
tool calls (`Failed to parse input at pos N: </s>`), fixed upstream in b10154.

## Canonical binary

- **Path:** `/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llama.cpp/build/bin/llama-server`
- **Current version:** **b10154** (`0e4a03622`), Darwin arm64.
- **Minimum required version (floor):** **b10154**. This is the first build that
  parses Mistral-Small-3.2 tool calls correctly. **Never run the canonical
  binary below this floor.**

## Policy

1. **Do not regress below the floor.** The canonical `llama-server` must always
   report `--version` ≥ `10154`. A lower version is a release blocker for local
   model serving.
2. **Verify before adopting a new build as canonical.** After any rebuild /
   `git pull` of `llama.cpp`, before pointing the manager at it:
   - `llama-server --version` prints a build number ≥ the floor;
   - a tools-mode smoke test succeeds (start a `--jinja` model, issue one tool
     call, confirm no `</s>` parse error);
   - record the new build number + commit hash + date in the log table below.
3. **Rebuild discipline.** Do not rebuild the canonical `build/` in place without
   recording old → new commit in the log below. A silent in-place rebuild is the
   regression vector this policy exists to prevent. Prefer a clean, intentional
   upgrade over an incidental one riding along with unrelated `llama.cpp` work.
4. **Per-model pinning for exceptions.** If one model needs a specific/newer
   build while others stay on the canonical one, pin it per-model instead of
   moving the global path (KNOWN-ISSUES I3):
   `llamacpp-manager config update <model> --llama-server-path /path/to/llama-server`.
   An empty value clears the override and falls back to the global path.
5. **Source of truth.** The global `llama_server_path` in the Application Support
   `config.yaml` is authoritative for the default binary; this document is
   authoritative for the version floor and the upgrade process.

## Verification commands

```bash
# current canonical version
"$(grep '^llama_server_path' ~/Library/Application\ Support/llamaCPPManager/config.yaml | sed 's/^llama_server_path:[[:space:]]*//')" --version

# per-model pin
llamacpp-manager config update <model> --llama-server-path /path/to/llama-server
```

## Canonical-build log

| Date       | Build  | Commit     | Notes                                                        |
|------------|--------|------------|--------------------------------------------------------------|
| 2026-07-27 | b10154 | 0e4a03622  | Adopted as canonical; fixes Mistral-Small-3.2 tool-call crash (floor). |
