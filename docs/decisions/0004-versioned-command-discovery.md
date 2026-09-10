# 0004: Versioned Machine-Readable Command Discovery

Status: Accepted
Date: 2026-09-10

## Authorization and Scope

The owner approved decisions 1–4 of the command-catalog proposal and the bounded implementation, with explicit clarifications for exit statuses, external IDs, availability reasons and inventory compatibility. Implement `dots commands --json` using the existing shared projections and `Resolver.Discover(false)`. This extends the discovery boundary of [0003](0003-trusted-external-command-protocol.md); its root, metadata, routing, execution and trust rules remain unchanged. Historical decisions and evidence are preserved.

## Catalog Schema 1

Output one UTF-8 JSON object with `schema_version: 1` and `commands: []`, using two-space indentation and a final newline. This version is independent of sidecar and doctor schemas. Every record has exactly the following initial fields; no collection is null:

| Field | Type and meaning |
| --- | --- |
| `kind` | `builtin` or `external` |
| `id` | String from shared metadata; the pair `(kind, id)` identifies a record, not an invocation. External IDs are canonical route tokens joined with hyphens, exactly as in the existing projection. |
| `route` | Array of canonical route tokens; empty for global-only version |
| `global_options` | Array of global invocation spellings, including `--version` on the version entry |
| `aliases` | Array of token arrays |
| `summary`, `synopsis` | Descriptive strings; synopsis is not a machine argument grammar |
| `examples` | Array of example strings in author order |
| `platforms`, `capabilities` | Arrays of declared support/requirements; built-ins may use the sole wildcard `*` |
| `hidden` | Boolean visibility flag |
| `outputs` | Array of objects with `format` (string) and `schema_version` (integer); text uses 0 |
| `mutation` | Existing classification string; external `read-only` remains an author assertion |
| `availability` | Object with `status` and `reason`, as below |

Include hidden and unavailable definitions. Human listing retains its existing hidden filtering. All shipped built-ins are available without probes. External availability comes directly from discovery: `status: "available"` requires `reason: null`; `status: "unavailable"` requires stable code `unavailable` or `unsupported_launcher`, mapped from typed categories, never diagnostic text. The coarse `unavailable` category covers platform policy and missing native executables without claiming finer cause classification. Unexpected internal availability categories fail closed instead of producing a misleading record.

Availability means static eligibility, not successful execution, authentication, sandboxing or protection against concurrent trusted-file replacement. Do not export resolved executable paths, root paths, environment values, timestamps or handler details. Author-provided descriptive strings are reproduced, not a promise of redacting arbitrary sidecar contents.

Order built-ins before externals and sort each group by ID using bytewise comparison. Sort global spellings, platforms and capabilities bytewise; sort aliases lexicographically by their token arrays (shorter prefix first), and outputs by format. Preserve canonical route and example order. Serialization uses the field order in the table; consumers must not depend on JSON object key order or whitespace. Sorting must not mutate shared metadata.

Schema 1 permits additive fields and changing command inventory without a version bump. Breaking changes to structure, field types or established meanings require a new schema version. Consumers ignore unknown fields, reject unsupported versions and treat unknown availability states conservatively. IDs are not shell expressions; invoke using routes/global spellings and let the dispatcher revalidate current state.

## Modes, Failures and Trust

`commands --json` is mutually exclusive with `--check`, `-h` and `--help`; repeats and extra arguments are usage errors. `commands --check` retains its stricter current-platform executable validation. JSON listing uses ordinary discovery and succeeds with valid unavailable records.

- Success: exit 0, JSON only on stdout and empty stderr. No logo, styling, progress or validation-success text.
- Dispatcher/prefix syntax errors, including more than eight roots: exit 2, diagnostic on stderr, empty stdout.
- Discovery validation/access/collision/resource-limit failures: exit 1, diagnostic on stderr, empty stdout. Validate all definitions, including hidden entries, before serializing the complete catalog. No partial catalog or JSON error envelope.
- Serialization/writer errors returned to the CLI: exit 1 with a fixed stderr diagnostic. A failed write can leave incomplete stdout. Native signal behavior is unchanged; consumers must reject incomplete output.

Only explicit repeatable prefix `--command-dir` roots participate. No roots yields built-ins only without platform collection or implicit search. Preserve decision 0003 limits, identity/case/file rules and protected namespaces. Existing built-ins/help resolve before root-health inspection; discovery itself checks selected roots. Never execute extensions for metadata, help, discovery or capability probing. Direct dispatch remains targeted and has no catalog enumeration dependency. No persistent cache.

## Implementation and Validation

The private CLI owns public catalog types and rendering over `Registry.Project()` and external projections. Do not expose private Go structs as the wire format or add I/O dependencies to pure dispatch. Update command metadata to advertise JSON schema 1. The same metadata remains suitable for future completion and Markdown consumers, without adding generators or a second command table now.

Require isolated schema/projection/order/availability tests, native process stream/status/nonexecution/snapshot tests, resource-limit failures and preserved routing/console-cleanup regressions. Verify with Go 1.27.1 and standard-library-only dependencies on native Termux, Linux and Windows. Measure JSON discovery separately with the existing 3 batches, 20 warmups and 200 samples per command per batch; timings remain advisory under decision 0002. Retain new source/binary/raw evidence separately from history. Results belong in the focused plan.

Completion generation, configuration loading, installation, bootstrap, package changes, dotfile mutation and releases remain outside this slice. No production OS floor or deferred platform capability becomes supported through catalog work.
