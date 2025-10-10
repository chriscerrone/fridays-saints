
import requests
import sys
import os

#
#     Hello!
#
#
# Replace this with the sheet ID found in the URL of your google drive sheet link:
# https://docs.google.com/spreadsheets/d/{THIS PART HERE}/edit?gid=0#gid=0 

sheetID = "19t7cfqnmQv5bNlTqN6zT9lDhc_BzZf1moXXYcRrVvjo"


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

# Continue using the same output filename
tmp_prefix = "tmp-"
live_prefix = "../../"
mute_file = "input-gain-steps.txt"
sample_file = "sample-steps.txt"
reverb_files = {
    1: "reverb_1-steps.txt",
    2: "reverb_2-steps.txt",
    3: "reverb_3-steps.txt",
}
sequencer_file = "step-sequencer-info.txt"
manual_file = "step-is-manual.txt"

def timestamp_to_milliseconds(timestamp):
    """
    Converts a timestamp in the format MM:SS.MMM or M:SS.MMM into total milliseconds.
    
    Args:
        timestamp (str): The timestamp string (e.g., "10:29.824").
    
    Returns:
        int: Total milliseconds.
    """
    try:
        # Split the timestamp into minutes, seconds, and milliseconds
        minutes, rest = timestamp.strip('"').split(":")
        seconds, milliseconds = rest.split(".")
        
        # Convert each component to integers
        minutes = int(minutes)
        seconds = int(seconds)
        milliseconds = int(milliseconds)
        
        # Calculate total milliseconds
        total_milliseconds = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
        return total_milliseconds
    except ValueError:
        # Return None if the timestamp is invalid
        return None

# Open and read the input file as a string
with open(input_file, 'r') as f:
    data = f.read()

# Split the string into rows
lines = data.splitlines()
output_lines = []

# Parse the lines into a list of steps and values
rows = []
first_real_row = 9999999999999
for idx, line in enumerate(lines):
    # Split the line into columns using ,s
    columns = line.split(',')
    if("Cue Information" in line):
        first_real_row = idx+2
    
    # Ensure the row has enough columns and try conv"erting to integers
    try:
        auto_manual = columns[1].strip('"')
        step = columns[2].strip('"')
        millis = timestamp_to_milliseconds(columns[3].strip('"'))
        reset = columns[5].strip('"')
        play_stop = columns[7].strip('"')
        filename = columns[8].strip('"')
        fadetime = columns[9].strip('"')
        mute_muteUnmute = columns[10].strip('"')
        mute_channel = columns[11].strip('"')
        mute_fadetime = columns[12].strip('"')
        reverb_channel = columns[13].strip('"')
        reverb_number = columns[14].strip('"')
        reverb_onoff = columns[15].strip('"')
        reverb_fadetime = columns[16].strip('"')
        if(idx >= first_real_row):
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
                "reverb_fadetime": reverb_fadetime,
            }
            rows.append(record)
    except (IndexError, ValueError):
        print("here?")
        print("error!!!!")
        print(IndexError)
        # Skip rows that don't have enough data or have invalid integers
        continue
    
# =================== do the steps-is-manual =====================
    
output_lines = []
for row in rows:
    if(row['auto_manual'] == 'manual'):
        output_lines.append(""+row['step'].strip('"')+", "+str(1)+";")

with open(tmp_prefix+manual_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))

# =================== do the sample-steps.txt =====================

output_lines = []
last_real_cue = -1
samples_instructions = ""
for idx, row in enumerate(rows):
    if(row['step']!=''):
        if(last_real_cue!=-1 and len(samples_instructions)>1):
            output_lines.append(str(last_real_cue)+","+samples_instructions+";")
        last_real_cue = row['step'].strip('"')
        samples_instructions = ""
    play = row['play_stop']
    if((play == "play") or (play == "stop")):
        try:
            play_stop = 0
            if(play == "play"):
                play_stop = 1
            sample = row['filename']
            fadetime = int(row['fadetime'])
            samples_instructions += " "+str(sample)+" "+str(play_stop)+" "+str(fadetime)
        except Exception as e:
            print("issue reading fade time! Is it a number? problem with line: \n"+str(row))
            print(e)
if(last_real_cue!=-1 and len(samples_instructions)>1):
    output_lines.append(str(last_real_cue)+","+samples_instructions+";")

with open(tmp_prefix+sample_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))



# =================== do the input-gain-steps.txt =====================

output_lines = []
last_real_cue = -1
mute_instructions = ""
for idx, row in enumerate(rows):
    if(row['step']!=''):
        if(last_real_cue!=-1 and len(mute_instructions)>1):
            output_lines.append(str(last_real_cue)+","+mute_instructions+";")
        last_real_cue = row['step'].strip('"')
        mute_instructions = ""
    granonoff = row['mute_muteUnmute']
    if((granonoff == "mute") or (granonoff == "unmute")):
        try:
            onoff = 0
            if(granonoff == "unmute"):
                onoff = 1
            channel = row['mute_channel']
            fadetime = int(row['mute_fadetime'])
            mute_instructions += " "+str(channel)+" "+str(onoff)+" "+str(fadetime)
        except Exception as e:
            print("issue reading fade time! Is it a number? problem with line: \n"+str(row))
            print(e)
if(last_real_cue!=-1 and len(mute_instructions)>1):
    output_lines.append(str(last_real_cue)+","+mute_instructions+";")

with open(tmp_prefix+mute_file, 'w') as f:
    print("outputting "+str(len(output_lines))+" lines to "+ f.name)
    f.write("\n".join(output_lines))

# =================== do the reverb-steps (split into 3 files) =====================

# Each output line format remains: "<step>, <channel on/off fadetime>...;"
# but we now write separate files for reverb #1, #2, #3.

# We'll accumulate per-cue strings for each reverb id independently.
per_reverb_output_lines = {1: [], 2: [], 3: []}

last_real_cue = -1
# current instruction strings for each reverb during the ongoing cue
current_instr = {1: "", 2: "", 3: ""}

def _flush_reverb_cue(last_cue, buckets, out_dict):
    """If we have accumulated strings for a finished cue, push lines to out_dict."""
    if last_cue == -1:
        return
    for r_id in (1, 2, 3):
        if len(buckets[r_id]) > 1:  # something accumulated (starts with a space)
            out_dict[r_id].append(f"{last_cue},{buckets[r_id]};")

for idx, row in enumerate(rows):
    # When a new step begins, flush the previous cue to all three reverb buckets
    if row['step'] != '':
        _flush_reverb_cue(last_real_cue, current_instr, per_reverb_output_lines)
        last_real_cue = row['step'].strip('"')
        current_instr = {1: "", 2: "", 3: ""}

    # Only process rows that actually toggle reverb
    play = row['reverb_onoff']
    if play in ("on", "off"):
        # Parse which reverb (1/2/3). Skip anything not 1–3.
        try:
            rnum = int(str(row['reverb_number']).strip().strip('"'))
        except Exception:
            continue
        if rnum not in (1, 2, 3):
            continue

        try:
            onoff = 1 if play == "on" else 0
            channel = row['reverb_channel']
            fadetime = int(row['reverb_fadetime'])
            current_instr[rnum] += f" {channel} {onoff} {fadetime}"
        except Exception as e:
            print("issue reading reverb fields! problem with line: \n" + str(row))
            print(e)

# Flush the final cue after the loop ends
_flush_reverb_cue(last_real_cue, current_instr, per_reverb_output_lines)

# Write tmp files for each reverb id
for r_id in (1, 2, 3):
    out_path = tmp_prefix + reverb_files[r_id]
    with open(out_path, 'w') as f:
        print(f"outputting {len(per_reverb_output_lines[r_id])} lines to {f.name}")
        f.write("\n".join(per_reverb_output_lines[r_id]))

# =================== do the step-sequencer-info.txt =====================

output_lines = []
for idx, row in enumerate(rows):
    if(row['step']!='' and row['auto_manual']!='manual'):
        resetbit = ""
        if(row['reset']=='yes'):
            resetbit = " reset"
        lineToPrint = ""+str(row['step'])+", "+str(row['millis']) +resetbit+";"
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

# Files to report on
output_files = [
    (tmp_prefix + manual_file,          live_prefix + manual_file),
    (tmp_prefix + sample_file,          live_prefix + sample_file),
    (tmp_prefix + mute_file,            live_prefix + mute_file),
    (tmp_prefix + reverb_files[1],      live_prefix + reverb_files[1]),
    (tmp_prefix + reverb_files[2],      live_prefix + reverb_files[2]),
    (tmp_prefix + reverb_files[3],      live_prefix + reverb_files[3]),
    (tmp_prefix + sequencer_file,       live_prefix + sequencer_file),
]


# Get max filename width for alignment
max_name_len = max(len(outfile) for _, outfile in output_files)

# Display changes
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

# Confirm overwrite
answer = input("\nConfirm overwriting old files? y/n: ").strip().lower()
if answer != 'y':
    print("Aborting. No files overwritten.")
    sys.exit(0)

# Make archive folder
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
archive_dir = os.path.join("z_old", timestamp)
os.makedirs(archive_dir, exist_ok=True)

# Archive and overwrite
for tmp_file, outfile in output_files:
    if os.path.exists(outfile):
        archived_path = os.path.join(archive_dir, os.path.basename(outfile))
        shutil.copy(outfile, archived_path)
        print(f"Archived: {outfile} -> {archived_path}")
    os.replace(tmp_file, outfile)
    print(f"Updated:  {outfile}")

try:
    os.replace('z_old_data.csv', archive_dir+"/"+'data.csv')
except:
    pass


print("\n✅ All files updated and old versions archived.")
