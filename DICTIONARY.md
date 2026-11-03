# ICE facility, office and jurisdiction references — dictionary

All original source fields retain their source meanings. The table unit and time semantics below are required context; names alone do not define a universal measure. Exact NULL counts are distinct from empty strings, empty geometry and source-coded missingness. See README for known anomalies and the immutable source lock.

## facilities

One detention-facility directory record; not a detention event or historical facility panel. Time semantics: reference snapshot, not historical panel.

Candidate key: No asserted natural key; preserve _source_row.

| Field | SQL type | NULL rows | Meaning |
|---|---|---:|---|
| `_source_row` | BIGINT | 0 | Ordinal in the pinned source member; not a cross-release entity key. |
| `detention_facility_code` | VARCHAR | 1 | ICE facility code; one source NULL is retained. |
| `name` | VARCHAR | 0 | Facility name reported by the source; names are not stable facility identifiers. |
| `address` | VARCHAR | 73 | Institutional street address as recorded by the source. |
| `city` | VARCHAR | 73 | City label associated with the reported address. |
| `county` | VARCHAR | 76 | County containing the geocoded facility, where identified. |
| `county_fips_code` | VARCHAR | 76 | County geographic identifier retained as text; missing geography is preserved. |
| `core_based_statistical_area` | VARCHAR | 166 | Core-based statistical area name assigned to the facility location. |
| `core_based_statistical_area_code` | VARCHAR | 166 | Text identifier of the assigned core-based statistical area. |
| `core_based_statistical_area_type` | VARCHAR | 166 | Source designation of metropolitan or micropolitan area type. |
| `combined_statistical_area` | VARCHAR | 356 | Combined statistical area name assigned to the facility location. |
| `combined_statistical_area_code` | VARCHAR | 356 | Text identifier of the assigned combined statistical area. |
| `state` | VARCHAR | 0 | State or territory label associated with the source location. |
| `state_fips_code` | VARCHAR | 76 | State FIPS identifier retained as text; do not coerce leading zeros away. |
| `zip` | VARCHAR | 73 | Postal ZIP code retained as text, preserving leading zeros. |
| `address_full` | VARCHAR | 73 | Source-combined institutional address string. |
| `latitude` | DOUBLE | 75 | Source point latitude in decimal degrees; missing coordinates are not imputed. |
| `longitude` | DOUBLE | 75 | Source point longitude in decimal degrees; missing coordinates are not imputed. |
| `field_office` | VARCHAR | 73 | ERO office responsible for the facility location; not a verified name key to the office table. |
| `federal_court_district_of_confinement` | VARCHAR | 72 | Federal judicial district assigned to the facility location; not by itself a legal-venue determination. |
| `federal_court_circuit_of_confinement` | VARCHAR | 72 | Federal circuit assigned to the facility location; not by itself a legal-venue determination. |

## offices

One office directory record across ERO, HSI and other listed agencies; not an ERO-only jurisdiction. Time semantics: reference snapshot, not historical panel.

Candidate key: No asserted natural key; preserve _source_row.

| Field | SQL type | NULL rows | Meaning |
|---|---|---:|---|
| `_source_row` | BIGINT | 0 | Ordinal in the pinned source member; not a cross-release entity key. |
| `office_name` | VARCHAR | 0 | Source office label; not unique across the office directory and not a universal join key. |
| `office_name_short` | VARCHAR | 121 | Short source office label, when provided. |
| `agency` | VARCHAR | 0 | Source agency represented in this directory, including ERO, HSI and other offices; only AOR maps are ERO-specific. |
| `field_office_name` | VARCHAR | 154 | Parent field-office label for the source office; NULL may indicate no parent provided. |
| `office_type` | VARCHAR | 0 | Original string, including Field office and Sub-office. |
| `address` | VARCHAR | 5 | Institutional street address as recorded by the source. |
| `city` | VARCHAR | 0 | City label associated with the reported address. |
| `state` | VARCHAR | 0 | State or territory label associated with the source location. |
| `zip` | VARCHAR | 1 | Postal ZIP code retained as text, preserving leading zeros. |
| `zip_4` | VARCHAR | 1 | Original full postal ZIP or ZIP+4 value, retained as text; 265 five-character ZIPs, nine complete ten-character ZIP+4 strings and one NULL in this snapshot. |
| `address_full` | VARCHAR | 5 | Source-combined institutional address string. |
| `area` | VARCHAR | 50 | Original description of office responsibility; wording and inconsistencies are retained. |
| `latitude` | DOUBLE | 5 | Source point latitude in decimal degrees; missing coordinates are not imputed. |
| `longitude` | DOUBLE | 5 | Source point longitude in decimal degrees; missing coordinates are not imputed. |

## aor

One ERO area-of-responsibility record; 25 geographic areas plus one nongeographic HQ placeholder. Time semantics: reference snapshot, not historical panel.

Candidate key: No asserted natural key; preserve _source_row.

| Field | SQL type | NULL rows | Meaning |
|---|---|---:|---|
| `_source_row` | BIGINT | 0 | Ordinal in the pinned source member; not a cross-release entity key. |
| `office_name` | VARCHAR | 1 | Source office label; not unique across the office directory and not a universal join key. |
| `area_of_responsibility_name` | VARCHAR | 0 | Source AOR identifier/label, including the nongeographic HQ placeholder. |
| `geometry_wkb` | BLOB | 0 | Original WKB; NAD83 EPSG:4269 for AOR tables. Empty HQ geometry retained. |

## county_aor

One county-to-ERO-area assignment record; 3,230 county records plus one nongeographic HQ placeholder. Time semantics: reference snapshot, not historical panel.

Candidate key: No asserted natural key; preserve _source_row.

| Field | SQL type | NULL rows | Meaning |
|---|---|---:|---|
| `_source_row` | BIGINT | 0 | Ordinal in the pinned source member; not a cross-release entity key. |
| `STATEFP` | VARCHAR | 1 | Two-character Census state FIPS code; NULL for the HQ placeholder. |
| `COUNTYFP` | VARCHAR | 1 | Three-character Census county FIPS code within state; NULL for HQ. |
| `COUNTYNS` | VARCHAR | 1 | Census county National Standard/ANSI identifier retained as text. |
| `GEOIDFQ` | VARCHAR | 1 | Fully qualified Census geographic identifier retained verbatim. |
| `GEOID` | VARCHAR | 1 | Five-character state-plus-county FIPS identifier; NULL for HQ. |
| `NAME` | VARCHAR | 1 | Census county name without the legal/statistical area description. |
| `NAMELSAD` | VARCHAR | 1 | Census county name including the legal/statistical area description. |
| `STUSPS` | VARCHAR | 1 | Census state or territory postal abbreviation. |
| `STATE_NAME` | VARCHAR | 1 | Census state or territory name. |
| `LSAD` | VARCHAR | 1 | Census legal/statistical area description code, retained as text. |
| `ALAND` | DOUBLE | 1 | Census land area in square meters; not an enforcement measure. |
| `AWATER` | DOUBLE | 1 | Census water area in square meters; not an enforcement measure. |
| `office_name` | VARCHAR | 1 | Source office label; not unique across the office directory and not a universal join key. |
| `notes` | VARCHAR | 3,134 | Source caveats about the county-to-office assignment. |
| `area_of_responsibility_name` | VARCHAR | 0 | Source AOR identifier/label, including the nongeographic HQ placeholder. |
| `geometry_wkb` | BLOB | 0 | Original WKB; NAD83 EPSG:4269 for AOR tables. Empty HQ geometry retained. |
