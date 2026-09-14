# Milestone 1 Challenger Handoff Report: FITS & I/O Engine

**Agent**: `challenger_m1_1` (Empirical Challenger: FITS & I/O)  
**Date**: 2026-09-14  
**Project**: Frontier Astronomy AI Discovery Suite  
**Working Directory**: `G:\frontier_astronomy_ai\.agents\challenger_m1_1`  
**Targets Evaluated**: `frontier_astronomy/ingestion/fits_reader.py`, `frontier_astronomy/ingestion/catalog.py`, `tests/test_adversarial_fits.py`  

---

## 1. Observation

### 1.1 Speed & Scale Benchmarking
- **20,000 Cadence Latency Verification**:
  - Target requirement: `< 20 ms` for 20,000 rows.
  - Tested across 50 consecutive runs with 10% non-zero quality flags in `tests/test_adversarial_fits.py::TestParserSpeedPerformance::test_20k_cadences_latency_threshold`.
  - Verbatim timing output:
    ```
    [PERFORMANCE] 20,000 cadences: Mean=0.56ms, Median=0.53ms, P95=0.77ms, Max=0.90ms
    ```
  - Result: Requirement is **EXCEEDED BY 25x**.
- **Extreme Cadence Scaling**:
  - 100,000 cadences: parsed and normalized in **4.26 ms**.
  - 250,000 cadences (multi-year continuous survey baseline): created in 7.90 ms, parsed and normalized in **11.58 ms**, retaining all 250,000 cadences.

### 1.2 Boundary & Truncation Handling
- **Zero-Row Tables**: Correctly parsed `NAXIS2 = 0` binary tables into 0-length NumPy arrays without division-by-zero or indexing errors (`tests/test_adversarial_fits.py::test_zero_row_bintable`).
- **Single-Row Tables**: Successfully parsed and normalized `NAXIS2 = 1` tables without errors.
- **Empty & Severed Streams**:
  - Completely empty bytes (`b""`): raises `ValueError("No binary table extension found in FITS stream.")`.
  - Truncated header (`< 2880` bytes): raises `ValueError("No binary table extension found in FITS stream.")`.
  - Missing BINTABLE extension (Primary HDU only): raises `ValueError("No binary table extension found in FITS stream.")`.
  - Severed table payload (cut mid-row): raises buffer/deserialization exception.

### 1.3 Discovered Vulnerabilities & Bugs

#### Vulnerability 1: Blank FITS Card with Comment Causes Coordinate Parsing Crash
- **File & Lines**: `frontier_astronomy/ingestion/fits_reader.py:48-69` and `fits_reader.py:250-251`
- **Observed Behavior**:
  When a FITS file contains an unassigned coordinate card such as:
  ```
  RA_OBJ  =                      / Right ascension (deg)
  ```
  `_parse_card_value(val_part)` splits on `/` to yield `val_str = ""`. Attempting `int("")` fails, and `except ValueError: return val_str` returns the empty string `""` instead of `None`.
  In `read_fits_light_curve`:
  ```python
  ra = float(pri_hdr.get("RA_OBJ", pri_hdr.get("RA", ext_hdr.get("RA_OBJ", 0.0))))
  ```
  Because `"RA_OBJ"` exists in `pri_hdr` with value `""`, `.get()` returns `""`, which causes:
  ```
  ValueError: could not convert string to float: ''
  ```
- **Reproduced in Test**: `tests/test_adversarial_fits.py::TestFITSHeaderVulnerabilities::test_empty_ra_obj_card_with_comment_crashes_parser`.

#### Vulnerability 2: Parquet Serialization Fails on NumPy Types in Metadata
- **File & Lines**: `frontier_astronomy/ingestion/catalog.py:306`
- **Observed Behavior**:
  `save_light_curve_parquet` invokes:
  ```python
  "user_metadata": json.dumps(lc.metadata)
  ```
  If `lc.metadata` contains common NumPy scalar types extracted from headers or numerical analysis (such as `np.int64`, `np.int32`, `np.float64`, or `np.ndarray`), Python's default `json.dumps` fails with:
  ```
  TypeError: Object of type int64 is not JSON serializable
  ```
- **Reproduced in Test**: `tests/test_adversarial_fits.py::TestParquetMetadataAdversarial::test_parquet_numpy_types_in_metadata_vulnerability`.

#### Vulnerability 3: Parquet Deserialization Crashes on Corrupted Coordinate Metadata
- **File & Lines**: `frontier_astronomy/ingestion/catalog.py:330-331`
- **Observed Behavior**:
  `load_light_curve_parquet` does:
  ```python
  ra = float(meta.get(b"ra", b"0.0").decode("utf-8"))
  dec = float(meta.get(b"dec", b"0.0").decode("utf-8"))
  ```
  While `user_metadata` parsing is protected by a `try...except Exception:` block, `ra` and `dec` conversions have no error handling. Corrupted or non-numeric metadata strings cause an unhandled `ValueError: could not convert string to float`.
- **Reproduced in Test**: `tests/test_adversarial_fits.py::TestParquetMetadataAdversarial::test_parquet_corrupted_ra_metadata_vulnerability`.

#### Vulnerability 4: Silent Drop of Differential / Negative Flux Cadences
- **File & Lines**: `frontier_astronomy/ingestion/fits_reader.py:294`
- **Observed Behavior**:
  `valid = (quality == 0) & np.isfinite(time) & np.isfinite(flux) & np.isfinite(flux_err) & (flux > 0)`
  For difference-imaging or background-subtracted light curves where flux is centered around 0.0 or negative, `(flux > 0)` silently drops all cadences $\le 0$. If all flux is negative, 100% of cadences are discarded and an empty `LightCurveData` is silently returned.
- **Reproduced in Test**: `tests/test_adversarial_fits.py::TestFITSHeaderVulnerabilities::test_negative_differential_flux_cadence_elimination`.

#### Flakiness Finding: Worker Detrending Unit Test Lacks Random Seed
- **File & Lines**: `tests/test_m1_ingestion_preprocessing.py:276-298`
- **Observed Behavior**:
  `noisy_flux = true_flux + np.random.normal(0.0, 0.0003, size=len(t))` without fixing `np.random.seed()`.
  `recovered_depth = 1.0 - np.min(norm_flux[in_transit])`
  `assert np.isclose(recovered_depth, depth, rtol=0.08)`
  Because `np.min` samples the Gaussian noise extremum, `recovered_depth` periodically reaches ~0.0163 ($> 0.015 \times 1.08 = 0.0162$), causing the test to fail intermittently in standard CI runs.

---

## 2. Logic Chain

1. **Performance**:
   - `fits_reader.py` directly executes `np.frombuffer` on structured big-endian dtypes over memory-mapped / in-memory byte buffers.
   - Because zero Python loops are used to iterate over rows, parsing 20,000 rows takes 0.56 ms (P95 0.77 ms) and 250,000 rows takes 11.58 ms.
   - Therefore, the latency requirement `< 20 ms for 20,000 rows` is unequivocally met and verified.

2. **Parsing Robustness**:
   - For valid standard Kepler/TESS files and basic variations (SAP-only, PDCSAP-only, missing quality flag, extra columns), the parser functions correctly.
   - For severed byte streams, the parser reliably detects truncated headers and truncated tables, raising exceptions rather than producing corrupted state.

3. **Vulnerabilities**:
   - The card parser does not re-strip after splitting comments (`if "/" in val_str: val_str = val_str.split("/", 1)[0].strip()`), failing to detect that a comment-only card has an empty value.
   - Parquet serialization assumes all metadata values are primitive Python types (int, float, str, dict), neglecting standard NumPy scalar types produced by astronomical arrays.
   - Quality filtering hardcodes `(flux > 0)` which is unsuitable for differential flux products.

---

## 3. Caveats

1. **No Implementation Changes Made**:
   In strict adherence to the Challenger role constraint (*Review-only — do NOT modify implementation code*), all vulnerabilities were demonstrated and verified strictly via tests in `tests/test_adversarial_fits.py`. No edits were made to `frontier_astronomy/`.
2. **Network/MAST Live Endpoints**:
   Adversarial testing was focused on local byte streams, FITS files, and Parquet serialization. Live MAST network rate limits or HTTP 5xx errors were not tested against the real STScI endpoint to avoid external dependencies.

---

## 4. Conclusion

**Verdict**: **ACCEPT WITH ADVERSARIAL HARDENING RECOMMENDATIONS**
- **Core Requirement Fulfillment**:
  - The pure-Python FITS ingestion engine is exceptionally performant (0.56 ms for 20,000 rows, exceeding the `< 20 ms` contract by a factor of 25x).
  - Scalability to 250,000 cadences is proven.
  - Parquet serialization round-trip is numerically exact for clean data.
- **Actionable Hardening Items for Worker**:
  1. In `fits_reader.py:_parse_card_value`: Add `if not val_str: return None` immediately following `val_str = val_str.split("/", 1)[0].strip()`.
  2. In `catalog.py:save_light_curve_parquet`: Pass a custom encoder or `default=str` to `json.dumps` to support NumPy scalars (`np.integer`, `np.floating`, `np.ndarray`).
  3. In `catalog.py:load_light_curve_parquet`: Wrap `float(...)` conversions of `ra` and `dec` in `try...except (ValueError, TypeError):` with default `0.0`.
  4. In `fits_reader.py:read_fits_light_curve`: Make `(flux > 0)` conditional on `np.nanmedian(flux) > 0` or add a parameter to allow non-positive differential flux.
  5. In `tests/test_m1_ingestion_preprocessing.py:276`: Add `np.random.seed(42)` to eliminate test flakiness in Savitzky-Golay transit recovery test.

---

## 5. Verification Method

To independently verify these findings and benchmarks:
1. Run the dedicated adversarial test suite:
   ```powershell
   python -m pytest tests/test_adversarial_fits.py -v -s
   ```
   *Expected result*: All 26 adversarial tests pass, printing latency benchmarks and confirming the exposed vulnerability assertions.
2. Inspect the adversarial test implementations in:
   - `tests/test_adversarial_fits.py`
