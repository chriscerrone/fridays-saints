import requests
import sys
import os
import csv

# ======== CONFIG ========
sheetID = "1sBLeF3VSvV0pIf2hzJcaeffZHRXLFG9wFwVOBMtlzJQ"
url = f'https://docs.google.com/spreadsheets/d/{sheetID}/gviz/tq?tqx=out:csv&sheet=0'

# ======== DOWNLOAD SHEET ========
print("requesting google sheet")
try:
    resp = requests.get(url)
    resp.raise_for_status()
except requests.exceptions.HTTPError as e:
    print("Error: could not download the Google Sheet.")
    print("  • Check the sheet ID and sharing (Anyone with the link can VIEW).")
    print(f"(HTTP {resp.status_code} – {e})")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print("Network error while downloading the Google Sheet:")
    print(f"  {e}")
    sys.exit(1)

if os.path.exists('data.csv'):
    os.replace('data.csv', 'z_old_data.csv')

with open('data.csv', 'wb') as f:
    f.write(resp.content)

# ======== HELPERS ========
def timestamp_to_milliseconds(timestamp: str):
    """Converts M:SS.mmm or MM:SS.mmm to ms. Returns None if invalid/blank."""
    if not timestamp:
        return None
    ts = timestamp.strip().strip('"')
    try:
        minutes, rest = ts.split(":")
        seconds, milliseconds = rest.split(".")
        return (int(minutes) * 60 * 1000) + (int(seconds) * 1000) + int(milliseconds)
    except Exception:
        return None

def ms_to_timestamp(ms: int) -> str:
    if ms is None:
        return ""
    minutes = ms // 60000
    rem = ms % 60000
    seconds = rem // 1000
    millis  = rem % 1000
    return f"{minutes}:{seconds:02d}.{millis:03d}"

def safe_str(row, idx):
    try:
        return (row[idx] if row[idx] is not None else "").strip()
    except IndexError:
        return ""

# ======== READ CSV ========
with open('data.csv', 'r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    csv_rows = list(reader)

# Detect start row (data begins 2 rows after a line containing "Cue Information")
first_real_row = None
for i, r in enumerate(csv_rows):
    if any(("Cue Information" in (c or "")) for c in r):
        first_real_row = i + 2
        break
if first_real_row is None:
    first_real_row = 1  # fallback: after header

# ======== PRINT NEW TIMESTAMPS (ONE PER ROW), PRESERVING EMPTIES ========
# Columns (0-based): step @ 2, timestamp @ 3, reset-after @ 5
baseline_ms = None
baseline_set = False
pending_reset = False  # handle reset==yes on a blank-timestamp row

for idx, r in enumerate(csv_rows):
    if idx < first_real_row:
        continue

    ts_raw = safe_str(r, 3)           # original timestamp
    reset  = safe_str(r, 5).lower()   # "yes" or ""

    if not ts_raw:
        # Preserve alignment with a blank line
        if reset == "yes":
            pending_reset = True
        print("")
        continue

    current_ms = timestamp_to_milliseconds(ts_raw)
    if current_ms is None:
        print("")
        continue

    # Compute elapsed using the *current* baseline
    if not baseline_set:
        # No baseline yet — treat first timestamp as baseline for elapsed calc
        elapsed_ms = 0
    else:
        elapsed_ms = current_ms - baseline_ms

    # Output ONLY the computed timestamp
    print(ms_to_timestamp(elapsed_ms))

    # Apply reset *after* printing, if requested (now or pending)
    if reset == "yes" or pending_reset:
        baseline_ms = current_ms
        baseline_set = True
        pending_reset = False
    else:
        # If no baseline yet, establish it after first printed row
        if not baseline_set:
            baseline_ms = current_ms
            baseline_set = True
