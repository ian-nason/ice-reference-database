# Validation of the local reference candidate

## Current audit corrections, November 3, 2026

The newly built candidate is `ice-reference.duckdb`: 26,226,688 bytes,
SHA-256 `c0c6f79bea8ad54e84c29103a7d854b68a381d931e104e2a3ccc03c1c80d70a5`.
The original database and manifest remain preserved. Each table now has its own
accurate unit in the source lock, README, HF card, dictionary and `_metadata`.
All four source tables and added row ordinals are unchanged. `_provenance`,
`_geometry_metadata` and `_columns` are also unchanged; embedded descriptions and
build timestamps are the intended metadata changes.

Eleven repository regression tests passed. They include optimized-Python smoke
failure cases, report no-clobber behavior, recursive budget accounting and a
disappearing WAL. The build now uses Parquet `file_row_number` and verifies its
association with every stored row. Validation-only reports use an explicit new
`--report` path and exclusive creation. Automatic extension installation is disabled.

The build ran in existing WSL tmpfs with the unchanged 128 MiB working cap and
512 MiB physical reserve. Copy-back preserved at least 128 MiB on Windows.
Existing source bytes/pins were reverified; no source acquisition or install ran.
The corrected artifact passed exact source checks and a read-only comparison
against all prior rows, including raw WKB. Additional checks confirmed EPSG:4269,
265 five-digit ZIPs, nine ZIP+4 values, one NULL ZIP, and no duplicate office
four-column keys.

Python Datapond 0.1.5 / DuckDB 1.5.6 and R Datapond 0.1.0 / DuckDB 1.5.5 passed
on this new artifact through localhost, with `PYTHONOPTIMIZE=2`. Fresh evidence
is in `evidence/audit-fix-*.json`; earlier receipts remain preserved.
The two companions' acquisition, safety and safety-test files are byte-identical,
closing the corresponding unread-code condition in Claude's source review.
The owner independently reviewed the implementation diff and the exact test/build/client scope. The original candidates remain archived separately.


The initial independent Claude source review completed under included Max usage and identified these corrections. Final corrected-source review is required before publication. These validation claims distinguish executed local checks from that separate source review. Public URL verification is recorded after upload; registry approval or merge is separate.
