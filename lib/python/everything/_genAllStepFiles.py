import requests
import sys
import os
import csv

#
#     Hello!
#
#
# Replace this with the sheet ID found in the URL of your google drive sheet link:
# https://docs.google.com/spreadsheets/d/{THIS PART HERE}/edit?gid=0#gid=0

sheetID = "1sBLeF3VSvV0pIf2hzJcaeffZHRXLFG9wFwVOBMtlzJQ"

#
# Additionally, make sure the sheet is set to at least anyone with the link can view
#
# Thanks!

url = f'https://docs.google.com/spreadsheets/d/{sheetID}/gviz/tq?tqx=out:csv&sheet=0'
print("requesting google sheet")
try:
    resp = requests.get(url)
    resp.raise_for_status()  # will raise HTTPError on bad status
except requests.exceptions.HTTPError as e:
    print("Error: could not download the Google Sheet.")
    print("  • Please check that your sheet ID is correct.")
    print("  • Make sure the Google Sheet’s sharing is set to 'Anyone with the link can VIEW.'")
    print(f"(HTTP {resp.status_code} – {e})")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    # catch other requests-related errors (network, DNS, etc.)
    print("Error: failed to download the Google Sheet due to a network issue:")
    print(f"  {e}")
    sys.exit(1)

input_file = 'data.csv'
if os.path.exists(input_file):
    print("moving old sheet to z_old_data.csv")
    os.replace(input_file, 'z_old_data.csv')

with open('data.csv', 'wb') as f:
    f.write(resp.content)

print("new google sheet downloaded as data.csv")

# =================== constants / helpers =====================

# Continue using the same output filename
tmp_prefix = "tmp-"
live_prefix = "../../"
mute_file = "input-gain-steps.txt"
sample_file = "sample-steps.txt"
reverb_files = {
    1: "reverb-steps_1.txt",
    2: "reverb-steps_2.txt",
    3: "reverb-steps_3.txt",
}
sequencer_file = "step-sequencer-info.txt"
manual_file = "step-is-manual.txt"
tremolo_file = "tremolo-steps.txt"


def timestamp_to_milliseconds(timestamp: str):
    """
    Converts a timestamp in the format MM:SS.MMM or M:SS.MMM into total milliseconds.
    Returns None if invalid/blank.
    """
    if not timestamp:
        return None
    ts = timestamp.strip().strip('"')
    try:
        minutes, rest = ts.split(":")
        seconds, milliseconds = rest.split(".")
        minutes = int(minutes)
        seconds = int(seconds)
        milliseconds = int(milliseconds)
        return (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
    except Exception:
        return None

def safe_int(val, default=None):
    try:
        return int(str(val).strip().strip('"'))
    except Exception:
        return default

def safe_str(row, idx):
    """Return trimmed string at index or empty string if missing."""
    try:
        return (row[idx] if row[idx] is not None else "").strip()
    except IndexError:
        return ""


# =================== read + parse csv robustly =====================

def _present(s: str) -> bool:
    return bool((s or "").strip().strip('"'))

def _fail(ctx: dict, message: str, offending_value=None):
    step_disp = (ctx.get("step") or "").strip('"') or "—"
    ts_raw    = (ctx.get("timestamp_raw") or "").strip('"')
    ts_ms     = ctx.get("timestamp_ms")
    ts_bits   = []
    if ts_raw:
        ts_bits.append(f"raw={ts_raw}")
    if ts_ms is not None:
        ts_bits.append(f"ms={ts_ms}")
    ts_part = " | timestamp: " + ", ".join(ts_bits) if ts_bits else ""
    print(f"\nERROR in CSV on line {ctx.get('line_no', '?')} | step: {step_disp}{ts_part}")
    print("  " + message)
    if offending_value is not None:
        print("  Offending value:", repr(offending_value))
    print("  (Tip: use the step/cue and timestamp to find the row in the Google Sheet.)")
    sys.exit(1)

def _must_be_int(ctx: dict, label: str, value: str, allow_empty=False):
    if not _present(value):
        if allow_empty:
            return None
        _fail(ctx, f"Missing integer for '{label}'.", value)
    try:
        return int(str(value).strip().strip('"'))
    except Exception:
        _fail(ctx, f"Expected integer for '{label}', got: {value!r}", value)

def _must_be_in(ctx: dict, label: str, value: str, allowed: set, allow_empty=False):
    v = (value or "").strip().strip('"')
    if not v:
        if allow_empty:
            return ""
        _fail(ctx, f"Missing value for '{label}'. Allowed: {sorted(allowed)}", value)
    if v not in allowed:
        _fail(ctx, f"Invalid value for '{label}': {v!r}. Allowed: {sorted(allowed)}", value)
    return v

def _validate_timestamp(ctx: dict, raw_val: str):
    """If raw timestamp cell is non-empty, it must parse to milliseconds."""
    if not _present(raw_val):
        return None
    ms = timestamp_to_milliseconds(raw_val)
    if ms is None:
        _fail(ctx, f"Bad timestamp format (expected M:SS.mmm or MM:SS.mmm), got: {raw_val!r}", raw_val)
    return ms

def _validate_groups(ctx: dict, row_dict: dict):
    """
    Enforce 'all or none' for grouped controls:
      - sample group: play_stop, filename, fadetime
      - mute group:   mute_muteUnmute, mute_channel, mute_fadetime
      - reverb group: reverb_onoff, reverb_channel, reverb_number
    Also validate enumerations and numeric fields when present.
    """

    # --- Sample group ---
    g_sample = [row_dict["play_stop"], row_dict["filename"], row_dict["fadetime"]]
    if any(_present(x) for x in g_sample):
        _ = _must_be_in(ctx, "play/stop", row_dict["play_stop"], {"play", "stop"})
        fn = row_dict["filename"].strip().strip('"')
        if not fn:
            _fail(ctx, "Filename present in sample group must be non-empty.", row_dict["filename"])
        _ = _must_be_int(ctx, "sample fadetime", row_dict["fadetime"])

    # --- Mute group ---
    g_mute = [row_dict["mute_muteUnmute"], row_dict["mute_channel"], row_dict["mute_fadetime"]]
    if any(_present(x) for x in g_mute):
        _ = _must_be_in(ctx, "mute_muteUnmute", row_dict["mute_muteUnmute"], {"mute", "unmute"})
        ch = row_dict["mute_channel"].strip().strip('"')
        if not ch:
            _fail(ctx, "mute_channel present in mute group must be non-empty.", row_dict["mute_channel"])
        _ = _must_be_int(ctx, "mute fadetime", row_dict["mute_fadetime"])

    # --- Reverb group ---
    g_rev = [row_dict["reverb_onoff"], row_dict["reverb_channel"], row_dict["reverb_number"]]
    if any(_present(x) for x in g_rev):
        _ = _must_be_in(ctx, "reverb_onoff", row_dict["reverb_onoff"], {"on", "off"})
        ch = row_dict["reverb_channel"].strip().strip('"')
        if not ch:
            _fail(ctx, "reverb_channel present in reverb group must be non-empty.", row_dict["reverb_channel"])
        rnum = _must_be_int(ctx, "reverb_number", row_dict["reverb_number"])
        if rnum not in (1, 2, 3):
            _fail(ctx, f"reverb_number must be 1, 2, or 3; got {rnum}", row_dict["reverb_number"])

    # --- Manual step constraint (if manual, require a valid step) ---
    if row_dict["auto_manual"].strip().strip('"') == "manual":
        st = row_dict["step"]
        if not _present(st):
            _fail(ctx, "auto_manual is 'manual' but 'step' is empty.", st)
        _ = _must_be_int(ctx, "step (manual row)", st)

    # # --- Tremolo group ---
    # # (expects: trem_onoff in {"on","off"}, trem_channel (int), trem_ms (int))
    # g_trem = [row_dict.get("trem_onoff", ""), row_dict.get("trem_channel", ""), row_dict.get("trem_ms", "")]
    # if any(_present(x) for x in g_trem):
    #     _ = _must_be_in(ctx, "trem_onoff", row_dict["trem_onoff"], {"on", "off"})
    #     _ = _must_be_int(ctx, "trem_channel", row_dict["trem_channel"])
    #     _ = _must_be_int(ctx, "trem_ms", row_dict["trem_ms"])


# Use csv.reader to correctly handle quoted commas, embedded newlines, etc.
with open(input_file, 'r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    csv_rows = list(reader)

rows = []
first_real_row = None

# detect the start: original logic used a line containing "Cue Information"
for idx, r in enumerate(csv_rows):
    if any(("Cue Information" in (c or "")) for c in r):
        first_real_row = idx + 2  # same +2 offset as before
        break

if first_real_row is None:
    # Fallback: if not found, assume after header (skip first row)
    first_real_row = 1

for idx, r in enumerate(csv_rows):
    if idx < first_real_row:
        continue
    # Build context used in all error messages for this row
    line_no = idx + 1  # human-friendly
    raw_step = safe_str(r, 2)
    raw_ts   = safe_str(r, 3)
    ctx = {
        "line_no": line_no,
        "step": raw_step,
        "timestamp_raw": raw_ts,
        "timestamp_ms": timestamp_to_milliseconds(raw_ts) if _present(raw_ts) else None,
    }

    # Pull with safe accessors (existing helpers)
    auto_manual      = safe_str(r, 1).strip('"')
    step             = raw_step.strip('"')
    millis_raw       = raw_ts
    millis           = _validate_timestamp(ctx, millis_raw)  # errors if malformed & non-empty
    reset            = safe_str(r, 5).strip('"')
    play_stop        = safe_str(r, 7).strip('"')
    filename         = safe_str(r, 8).strip('"')
    fadetime         = safe_str(r, 9).strip('"')
    mute_muteUnmute  = safe_str(r,10).strip('"')
    mute_channel     = safe_str(r,11).strip('"')
    mute_fadetime    = safe_str(r,12).strip('"')
    reverb_channel   = safe_str(r,13).strip('"')
    reverb_number    = safe_str(r,14).strip('"')
    reverb_onoff     = safe_str(r,15).strip('"')
    trem_onoff      = safe_str(r,16).strip('"')
    trem_channel    = safe_str(r,17).strip('"')
    trem_ms         = safe_str(r,20).strip('"')
    trem_depth      = safe_str(r,21).strip('"')
    trem_sqsi       = safe_str(r,22).strip('"')
    trem_distort_sr = safe_str(r,23).strip('"')
    trem_distort_bs = safe_str(r,24).strip('"')


    # basic skip if no content at all
    if not any([
        auto_manual, step, millis is not None, reset, play_stop, filename, fadetime,
        mute_muteUnmute, mute_channel, mute_fadetime,
        reverb_channel, reverb_number, reverb_onoff,
        trem_onoff, trem_channel, trem_ms, trem_distort_sr, trem_distort_bs, trem_sqsi, trem_depth
    ]):
        continue


    record = {
        "auto_manual": auto_manual,
        "step": step,
        "millis": millis,
        "reset": reset,
        "play_stop": play_stop,
        "filename": filename,
        "fadetime": fadetime,
        "mute_muteUnmute": mute_muteUnmute,
        "mute_channel": mute_channel,
        "mute_fadetime": mute_fadetime,
        "reverb_channel": reverb_channel,
        "reverb_number": reverb_number,
        "reverb_onoff": reverb_onoff,
        "trem_onoff": trem_onoff,
        "trem_channel": trem_channel,
        "trem_ms": trem_ms,
        "trem_depth": trem_depth,
        "trem_sqsi": trem_sqsi,
        "trem_distort_sr":trem_distort_sr,
        "trem_distort_bs":trem_distort_bs,

    }
    print(record)

    # Validate group completeness / enums / numerics with rich context
    _validate_groups(ctx, record)

    rows.append(record)












# =================== do the steps-is-manual =====================

output_lines = []
for row in rows:
    # print(row)
    if row['auto_manual'] == 'manual':
        output_lines.append(f"{row['step'].strip('\"')}, 1;")
# print(output_lines)
with open(tmp_prefix+manual_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))

# =================== do the sample-steps.txt =====================

output_lines = []
last_real_cue = -1
samples_instructions = ""
for row in rows:
    if row['step'] != '':
        if (last_real_cue != -1) and (len(samples_instructions) > 1):
            output_lines.append(f"{last_real_cue},{samples_instructions};")
        last_real_cue = row['step'].strip('"')
        samples_instructions = ""
    play = row['play_stop']
    if play in ("play", "stop"):
        try:
            play_stop = 1 if play == "play" else 0
            sample    = row['filename']
            fadetime  = safe_int(row['fadetime'], 0)
            samples_instructions += f" {sample} {play_stop} {fadetime}"
        except Exception as e:
            print("issue reading fade time! Is it a number? problem with line: \n"+str(row))
            print(e)
if (last_real_cue != -1) and (len(samples_instructions) > 1):
    output_lines.append(f"{last_real_cue},{samples_instructions};")

with open(tmp_prefix+sample_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))

# =================== do the input-gain-steps.txt =====================

output_lines = []
last_real_cue = -1
mute_instructions = ""
for row in rows:
    if row['step'] != '':
        if (last_real_cue != -1) and (len(mute_instructions) > 1):
            output_lines.append(f"{last_real_cue},{mute_instructions};")
        last_real_cue = row['step'].strip('"')
        mute_instructions = ""
    granonoff = row['mute_muteUnmute']
    if granonoff in ("mute", "unmute"):
        try:
            onoff    = 1 if granonoff == "unmute" else 0
            channel  = row['mute_channel']
            fadetime = safe_int(row['mute_fadetime'], 0)
            mute_instructions += f" {channel} {onoff} {fadetime}"
        except Exception as e:
            print("issue reading fade time! Is it a number? problem with line: \n"+str(row))
            print(e)
if (last_real_cue != -1) and (len(mute_instructions) > 1):
    output_lines.append(f"{last_real_cue},{mute_instructions};")

with open(tmp_prefix+mute_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))

# =================== do the reverb-steps (split into 3 files) =====================

per_reverb_output_lines = {1: [], 2: [], 3: []}

last_real_cue = -1
current_instr = {1: "", 2: "", 3: ""}

def _flush_reverb_cue(last_cue, buckets, out_dict):
    if last_cue == -1:
        return
    for r_id in (1, 2, 3):
        if len(buckets[r_id]) > 1:  # something accumulated (starts with a space)
            out_dict[r_id].append(f"{last_cue},{buckets[r_id]};")

for row in rows:
    if row['step'] != '':
        _flush_reverb_cue(last_real_cue, current_instr, per_reverb_output_lines)
        last_real_cue = row['step'].strip('"')
        current_instr = {1: "", 2: "", 3: ""}

    play = row['reverb_onoff']
    if play in ("on", "off"):
        try:
            rnum = safe_int(row['reverb_number'])
        except Exception:
            rnum = None
        if rnum not in (1, 2, 3):
            continue
        try:
            onoff    = 1 if play == "on" else 0
            channel  = row['reverb_channel']
            current_instr[rnum] += f" {channel} {onoff}"
        except Exception as e:
            print("issue reading reverb fields! problem with line: \n" + str(row))
            print(e)

_flush_reverb_cue(last_real_cue, current_instr, per_reverb_output_lines)

for r_id in (1, 2, 3):
    out_path = tmp_prefix + reverb_files[r_id]
    with open(out_path, 'w') as f:
        print(f"outputting {len(per_reverb_output_lines[r_id])} lines to {f.name}")
        f.write("\n".join(per_reverb_output_lines[r_id]))



# =================== do the tremolo-steps.txt =====================

output_lines = []
last_real_cue = -1
trem_instructions = ""

def _flush_trem(last_cue, buf, out_lines):
    if last_cue != -1 and len(buf) > 1:  # something accumulated (starts with a space)
        out_lines.append(f"{last_cue},{buf};")

for row in rows:
    if row['step'] != '':
        _flush_trem(last_real_cue, trem_instructions, output_lines)
        last_real_cue = row['step'].strip('"')
        trem_instructions = ""

    play = (row.get('trem_onoff') or '').strip().lower()
    if play not in ('on', 'off'):
        continue

    ch = safe_int(row.get('trem_channel'), None)
    if ch is None:
        print(f"Skipping tremolo entry at step {row.get('step','?')}: missing/invalid channel.")
        continue

    onoff = 1 if play == 'on' else 0

    # If OFF and trem_ms missing/invalid => default to 0; if ON and missing/invalid => skip
    tms_raw = row.get('trem_ms')
    tms = safe_int(tms_raw, None)
    if tms is None:
        if onoff == 0:
            tms = 0
        else:
            print(f"Skipping tremolo entry at step {row.get('step','?')}: 'on' requires trem_ms.")
            continue
    trem_sqsi = row.get('trem_sqsi')
    trem_depth = row.get('trem_depth')
    trem_distort_sr = row.get('trem_distort_sr')
    trem_distort_bs = row.get('trem_distort_bs')
    if trem_distort_sr == "":
        trem_distort_sr = 0
    if trem_distort_bs == "":
        trem_distort_bs = 0
    if trem_sqsi == "":
        trem_sqsi = 0
    if trem_depth == "":
        trem_depth = 0

    trem_instructions += f" {ch} {onoff} {tms} {trem_depth} {trem_sqsi} {trem_distort_sr} {trem_distort_bs}"

_flush_trem(last_real_cue, trem_instructions, output_lines)

with open(tmp_prefix + tremolo_file, 'w') as f:
    print(f"outputting {len(output_lines)} lines to {f.name}")
    f.write("\n".join(output_lines))






# =================== do the step-sequencer-info.txt =====================

output_lines = []
for row in rows:
    if (row['step'] != '') and (row['auto_manual'] != 'manual'):
        resetbit = " reset" if row['reset'] == 'yes' else ""
        millis_str = "" if row['millis'] is None else str(row['millis'])
        lineToPrint = f"{row['step']}, {millis_str}{resetbit};"
        output_lines.append(lineToPrint)

with open(tmp_prefix+sequencer_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))




# =================== print the output to the user for them to confirm =====================
import shutil
from datetime import datetime

def count_lines(filename):
    if not os.path.exists(filename):
        return 0
    with open(filename, 'r') as f:
        return sum(1 for _ in f)

def compare_files(file1, file2):
    if not os.path.exists(file1) or not os.path.exists(file2):
        return None
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()
        if lines1 == lines2:
            return 0
        diffs = sum(1 for a, b in zip(lines1, lines2) if a != b)
        diffs += abs(len(lines1) - len(lines2))
        return diffs

output_files = [
    (tmp_prefix + manual_file,          live_prefix + manual_file),
    (tmp_prefix + sample_file,          live_prefix + sample_file),
    (tmp_prefix + mute_file,            live_prefix + mute_file),
    (tmp_prefix + reverb_files[1],      live_prefix + reverb_files[1]),
    (tmp_prefix + reverb_files[2],      live_prefix + reverb_files[2]),
    (tmp_prefix + reverb_files[3],      live_prefix + reverb_files[3]),
    (tmp_prefix + tremolo_file,         live_prefix + tremolo_file),
    (tmp_prefix + sequencer_file,       live_prefix + sequencer_file),
]


max_name_len = max(len(outfile) for _, outfile in output_files)

print("\n======== File Line Changes ========")
for tmp_file, outfile in output_files:
    old_count = count_lines(outfile)
    new_count = count_lines(tmp_file)
    name_field = outfile.ljust(max_name_len)
    count_field = f"{str(old_count).rjust(4)} -> {str(new_count).ljust(4)}"

    change_note = ""
    if old_count == new_count:
        diff_count = compare_files(tmp_file, outfile)
        if diff_count == 0:
            change_note = "(no change)"
        elif diff_count is not None:
            change_note = f"({diff_count} changes)"

    print(f"{name_field} : {count_field}  {change_note}")

answer = input("\nConfirm overwriting old files? y/n: ").strip().lower()
if answer != 'y':
    print("Aborting. No files overwritten.")
    sys.exit(0)

timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
archive_dir = os.path.join("z_old", timestamp)
os.makedirs(archive_dir, exist_ok=True)

for tmp_file, outfile in output_files:
    if os.path.exists(outfile):
        archived_path = os.path.join(archive_dir, os.path.basename(outfile))
        shutil.copy(outfile, archived_path)
        print(f"Archived: {outfile} -> {archived_path}")
    os.replace(tmp_file, outfile)
    print(f"Updated:  {outfile}")

try:
    os.replace('z_old_data.csv', os.path.join(archive_dir, 'data.csv'))
except Exception:
    pass

print("\n✅ All files updated and old versions archived.")
