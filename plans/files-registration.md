# Existing-source file registration

**Status: Implemented; focused acceptance and real Termux registration verified.** Selected Todo: `887b2a48bac6435d8f7842d433f54ce9` (`add-files`).

## Agreed behavior

Extend existing files add/discover and the Add picker to register repository files,
whole directories and correct existing links. Infer repository ownership, save
identity/platform eligibility centrally and implementation in the active profile.
Use unique registered destinations or request one with interactive input/single-source
`--target`. Preserve ordinary import behavior. Scan includes ready sources and
reports unresolved candidates. Never follow nested directory links when registering.

One guarded Store transaction owns metadata, new links and applicable receipts.
Correct pre-existing links stay unchanged and unowned by uninstall; undo reverses
registration. New links retain installation recovery. Reject conflicts, unsafe
parents, unsupported objects, excluded owners and ambiguous destinations.

## Packages and dependencies

1. `47ef06369a53475ca3c1c541dd4cc8ac`: bounded discovery and classification.
2. `88ea4cfc342a47a0936848e7ec41ae73`: atomic registration/linking; depends on 1.
3. `b32a2f6460c840b6bf9771b49a3c3e52`: picker and shell interfaces; depends on 1–2.
4. `2205438c8f5340778da8eeb6e8dd0381`: verification/documentation; depends on 1–3.
5. `f29a638945044d0ab376132d6d199432`: real Termux registration; depends on 1–4.

Owner: dots-files-maintenance. Menu assessment: update existing Add workflow and
expose it in the Files launcher. Configuration assessment: no configuration
integration change needed; reuse mappings, files.backup and shared presentation.
No new preference registry. Bash and native PowerShell share controllers and
metadata; Windows uses its native destinations with no WSL translation.

## Acceptance

Isolated source/link/directory/import, exclusions, duplicate/conflicting claims,
stale previews, interruption/rollback/undo, receipts/uninstall and idempotence
checks. Cover picker cancellation, missing tools, mixed scan outcomes, JSON and
literal paths. Apply the [presentation gate](../docs/presentation.md#acceptance-gate)
at 40/80/120 columns. Run file-platform before affected lifecycle suites, then
catalog/profile/picker/Bash/native-controller and docs checks. Preserve unrelated
work. Rebuild/check the local wiki. Native Linux/WSL and Windows PowerShell 5.1/7
acceptance remains separately named when unavailable.

After isolated verification, preview and register ~/.termux through the CLI.
Compare link identity/text and non-dereferencing directory fingerprints, confirm
linked inventory and unchanged repeat preview, and record transaction/undo.
No commit, push, reload or theme activation is authorized by this work.

## Evidence

Before implementation, local discovery: repository 584 rows / 5.337 seconds;
system 257 rows / 1.326 seconds (single observational run, not a benchmark claim).
Current ~/.termux points to profiles/termux/config/termux. Nested colors.properties
and shell links must remain unchanged. The Termux location source is corrected to config/termux.


Focused verification: file-platform 5, registration 16 (including Windows readlink normalization), file operations 22, catalog 9, profile backend 14, mappings
29, repair 48, Bash 27, native controller 23 (2 unavailable-runtime skips), shared
menus 24, picker focused 15, launcher contracts 11 passed. Registration picker
used native FZF in isolated terminals at 40/80/120 columns with cancellation.
Bash/native JSON and four completion surfaces preserve literal paths and data.
Markdown validation: 1186 links; command metadata: 234 routes. Local wiki built
with transaction a8c5f559724249b8845121ffc78440a4 and checked healthy.

Existing acceptance limits: the FZF resource-search test waits for a 1/2 display
marker absent in the installed FZF rendering; the same timeout was reproduced
with original HEAD manage/catalog/picker modules in a disposable fixture. Three
installation-adapter tests and optional-source/update installation fail because their
partial runtime fixtures omit config_values; all five failures were reproduced
with original HEAD modules. The previously documented WSL theme-repeat/fingerprint
failure also remains (see profile-backend.md); ordinary file idempotence and
bundled installation checks pass independently. Native Linux/WSL and Windows
PowerShell 5.1/7 runtime/visual acceptance remains pending.

Performance investigation: a paired run observed 584 raw to 579 enriched candidates,
3.969 s enumeration + 1.921 s registered-link inspection + 3.365 s classification.
Profiling identified repeated pathlib ancestor construction; component comparisons
reduced observed classification to 1.160 s without a cache. Timings under concurrent
fixture load are variable (that later enumeration took 10.306 s). This is added
explicit discovery work; startup/help/completion do not enumerate candidates.

Broad installation run: 28 cases, 25 passed; the known WSL repeat failure and two incomplete runtime fixtures remain. ShellCheck and changed-script syntax pass. No new platform runtime claims.


Live acceptance: registered `termux:file-config-termux` with source `config/termux`,
target `${TERMUX}`, strategy `directory-link`, status `linked`. Transaction
`ef44023d4ea643eaba1d0722fa255893`; undo with
`dots files undo ef44023d4ea643eaba1d0722fa255893`. Link inode/text, directory digest
and nested links match before/after. Installation receipt and unrelated profile/
registry fields are unchanged; repeated CLI preview is unchanged and the planner
returns zero operations. Evidence: `/data/data/com.termux/files/usr/tmp/dots-files-registration-live-sldk0nyk/verification.json`.

All five child goals and the selected parent are complete. Changes remain
uncommitted in the main and wiki working trees. No push, reload or theme activation.
The final timing observation was 8.023 s enumeration + 2.374 s link inspection +
2.068 s classification (12.465 s total); variation precludes an overall speed claim.
