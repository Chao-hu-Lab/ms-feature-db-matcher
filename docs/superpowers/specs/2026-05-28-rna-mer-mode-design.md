# RNA / MeR Mode Design

## Summary

Add a compact second-level RNA subtype selector so users can choose whether RNA database matching includes R, MeR, or both. The first-level database selector should read as `DNA only`, `RNA only`, and `DNA + RNA`; the old visible label `Both` should no longer be shown because it does not explain whether RNA includes R, MeR, or both.

Default behavior remains equivalent to the current app: `DNA + RNA` with subtype `R + MeR`.

## Goals

- Let users run RNA database matching against `R only`, `MeR only`, or `R + MeR`.
- Keep the GUI simple: avoid expanding the main mode list into many combinations.
- Preserve existing behavior unless the user explicitly changes the RNA subtype.
- Keep `DNA + RNA` intuitive: it means DNA plus the selected RNA subtype scope.

## UX Design

The Matching Mode card has two controls:

- Database scope: `DNA only`, `RNA only`, `DNA + RNA`
- RNA subtype: `R`, `MeR`, `R + MeR`

The RNA subtype control is a small segmented row under the database scope, not another set of large tiles. It is enabled for `RNA only` and `DNA + RNA`, and disabled or visually muted for `DNA only`. The default selected subtype is `R + MeR`.

Effective meanings:

- `DNA only`: match DNA database only; ignore RNA subtype.
- `RNA only + R`: match RNA database and keep only R hits.
- `RNA only + MeR`: match RNA database and keep only MeR hits.
- `RNA only + R + MeR`: current RNA behavior.
- `DNA + RNA + R`: match DNA plus R hits.
- `DNA + RNA + MeR`: match DNA plus MeR hits.
- `DNA + RNA + R + MeR`: current full Both behavior.

## Matching Behavior

Introduce an RNA subtype concept separate from the database match mode. Suggested internal type:

- `RnaSubtypeMode.R_ONLY`
- `RnaSubtypeMode.MER_ONLY`
- `RnaSubtypeMode.R_AND_MER`

Existing R versus MeR classification remains based on the current rule:

- R: RNA database hit whose short name does not end with `m`
- MeR: RNA database hit whose short name ends with `m`

`Tags matched` remains active and intersects with the new subtype filter:

- If subtype is `R`, never output MeR even when tags allow `3`.
- If subtype is `MeR`, never output R even when tags allow `2`.
- If subtype is `R + MeR`, current tag behavior remains unchanged.

DNA matching, DNA `Matched Source`, formulas, rich-text colors, and multi-sheet export behavior remain unchanged.

## Interfaces

- `build_match_column(...)` should accept an RNA subtype argument with default `R + MeR` to preserve existing tests and direct callers.
- `run_matching(...)` should accept or derive the selected RNA subtype from GUI state.
- GUI state should store the subtype as a string variable alongside the existing match mode variable.
- Visible mode text should use `DNA only`, `RNA only`, and `DNA + RNA`; internal `MatchMode.BOTH` may remain for compatibility, but user-facing copy should not show `Both`.

## Tests

Add focused tests for:

- `RNA only + R` excludes MeR hits.
- `RNA only + MeR` excludes R hits.
- `RNA only + R + MeR` preserves current RNA behavior.
- `DNA + RNA + R` returns DNA plus R and excludes MeR.
- `DNA + RNA + MeR` returns DNA plus MeR and excludes R.
- `DNA only` ignores RNA subtype and does not require an RNA database.
- `Tags matched` and subtype filtering combine by intersection.
- GUI smoke tests verify default subtype is `R + MeR`, subtype is disabled for `DNA only`, and displayed database labels do not use `Both`.

## Acceptance Criteria

- Users can choose R, MeR, or R + MeR without selecting from a long list of combined modes.
- Existing default output remains unchanged when users do not touch the subtype selector.
- `DNA + RNA` is the user-facing replacement for `Both`.
- RNA-only mode still omits `Matched Source`; DNA-containing modes still include DNA `Matched Source`.
- The relevant pytest suite passes after implementation.
