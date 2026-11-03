---
license: cc0-1.0
pretty_name: ICE facility, office and jurisdiction references
---

# ICE facility, office and jurisdiction references

Frozen Datapond snapshot: 4 data tables, 4,410 stored source rows,
26,226,688 bytes. The catalog identifier requires separate registry integration.
Row totals mix table units and are not unique people, events or places.

| Table | Rows | Unit | Time semantics |
|---|---:|---|---|
| `facilities` | 878 | One detention-facility directory record; not a detention event or historical facility panel | reference snapshot, not historical panel |
| `offices` | 275 | One office directory record across ERO, HSI and other listed agencies; not an ERO-only jurisdiction | reference snapshot, not historical panel |
| `aor` | 26 | One ERO area-of-responsibility record; 25 geographic areas plus one nongeographic HQ placeholder | reference snapshot, not historical panel |
| `county_aor` | 3,231 | One county-to-ERO-area assignment record; 3,230 county records plus one nongeographic HQ placeholder | reference snapshot, not historical panel |

## Source, scope and limitations

Facility scope starts with locations used since January 2025 plus newly listed sites; it is not a complete historical directory. Source observation vintages vary. The facility repository commit is October 20, 2026, and the office repository commit is April 21, 2026. Neither is a universal observation date.

The facility table preserves one NULL detention_facility_code and 75 missing coordinate pairs. Use _source_row as a pinned-file row reference, not a cross-release entity key. Preserve leading zeros in ZIP/FIPS/GEOID. Office fields are office_type, latitude and longitude; six obsolete population-summary fields from older facility documentation are absent from this payload.

AOR and county-AOR geometry is retained as WKB with NAD83 EPSG:4269 metadata, despite older codebook prose naming EPSG:4326. No coordinates are transformed or relabelled. Each geography table retains its nongeographic HQ placeholder; exclude it explicitly when analyzing geographic coverage. Do not silently drop source rows merely because a county or office name is NULL.

The office directory includes ERO, HSI and other agencies. Its AOR geography tables describe ERO responsibility only, not HSI territories or a historical boundary panel. The source office lists are described as September 2025 and county geometry derives from Census 2024 boundaries. Harlingen's FY2022 split and other source boundary caveats matter for time-specific joins. Facility codes need release/year coverage checks before LEFT JOINs to detention events. Office-name variants require an explicit reviewed crosswalk; no fuzzy link or legal-venue inference is supplied.

Every source byte hash, immutable URL and repository commit is in
[source-lock.json](source-lock.json). Every row is retained; `_source_row` is added
as an ordinal within the pinned member. Geometry, when present, is stored as WKB
in `geometry_wkb`, with all original metadata in `_geometry_metadata`. `_provenance`,
`_metadata` and `_columns` document the build. [DICTIONARY.md](DICTIONARY.md) records
types, exact NULL counts, units and time semantics. Original source flags and text
are not coerced into new numeric categories.

Publisher: [Deportation Data Project](https://deportationdata.org/data/processed/ice.html).
Data license: CC0-1.0, as labelled by the publisher; see the retained license notes.
Cite government data collated by the Deportation Data Project and the pinned source
commit. Repository commit dates do not promise current observations or automatic refreshes.

## Local queries

```python
import duckdb
con = duckdb.connect('ice-reference.duckdb', read_only=True,
                     config={'memory_limit':'128MiB','threads':'1'})
try:
    print(con.sql('SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5').fetchall())
finally:
    con.close()
```

```r
library(DBI)
con <- dbConnect(duckdb::duckdb(), dbdir='ice-reference.duckdb', read_only=TRUE)
tryCatch({
  dbExecute(con, "SET memory_limit='128MiB'")
  dbExecute(con, 'SET threads=1')
  print(dbGetQuery(con, "SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5"))
}, finally=dbDisconnect(con, shutdown=TRUE))
```

Public datapond identifier `ice-reference` requires a future approved catalog release.
The smoke scripts use an isolated localhost registry, never a global registry edit.

## Reproduce and refresh

Use Python 3.11 or newer in a dedicated environment. Install the exact tested dependencies with `python -m pip install -r requirements.txt` (or use the pinned uv source in pyproject.toml), then:

```sh
python acquire_sources.py
python build_database.py --validate-only --report fresh-validation.json
python build_database.py --output fresh-ice-reference.duckdb
```

Downloads are pinned, bounded and SHA-verified; existing source files are checked
and reused. The importer preserves all source fields and compares every stored
row with the input using symmetric EXCEPT ALL. It uses one thread, 128 MiB DuckDB
memory, no spill, a 128 MiB working-file cap
and a 512 MiB physical free-space reserve. A watchdog interrupts work when a budget
is crossed. Builds are private until complete; hard-link publication refuses an
existing final database, manifest or orphan WAL path. Synchronous checks enforce the working-file cap and physical reserve after close and before publication; hash checks remain enabled under optimized Python. Failed/private files remain for inspection, with no cleanup
of unrelated work. Peak process memory can exceed DuckDB's buffer limit.

To refresh, review the publisher's changed files and definitions, update pins and
expected schemas/counts, run full source checks and Python/R smoke tests, and audit
both data and documentation. No scheduled or unattended refresh is configured.

Source documentation: [facilities](https://deportationdata.org/docs/ice/codebook-facilities.html) and [offices/AORs](https://deportationdata.org/docs/ice/codebook-offices.html). Actual pinned schemas and CRS override the older codebook discrepancies described above. Office names alone are not unique; the current `(agency, office_type, office_name, address_full)` combination is unique. Each geography table has one empty MULTIPOLYGON for HQ and no SQL-NULL geometry.

Validation commands: `python -m unittest -v test_safety.py` and `python run_smoke.py --python /path/to/python --rscript /path/to/Rscript --r-library /path/to/R/library`. The latter needs the released Python and R datapond packages and an already installed HTTPFS extension. It uses only localhost and this database. See VALIDATION.md for the executed versions and results.

## Snapshot files

[Download the database](https://huggingface.co/datasets/Nason/ice-reference-database/resolve/main/ice-reference.duckdb), [browse its files](https://huggingface.co/datasets/Nason/ice-reference-database/tree/main), or inspect the [reproducible source](https://github.com/ian-nason/ice-reference-database). Verify the snapshot SHA-256 `c0c6f79bea8ad54e84c29103a7d854b68a381d931e104e2a3ccc03c1c80d70a5` (26,226,688 bytes). The registry PR pins immutable Hugging Face revisions; a later `main` may refer to a newer snapshot.

Once the separate catalog entry is merged, use the released clients:

```python
import datapond
con = datapond.connect("ice-reference")
try:
    print(con.sql("SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5").fetchall())
finally:
    con.close()
```

```r
library(datapond)
con <- dp_connect("ice-reference")
tryCatch(print(DBI::dbGetQuery(con, "SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5")), finally=DBI::dbDisconnect(con, shutdown=TRUE))
```

Until catalog integration, the local Python/R examples above work with the downloaded snapshot. The smoke scripts exercise both released clients with an isolated registry and this same database.
