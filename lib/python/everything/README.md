# Python script for generating .txt files

This script is for using a google sheet like [this](https://docs.google.com/spreadsheets/d/1VDwPe9hKSHXVEZSls5vFoe_vihTM-lGpmwxSjNe8wNI/edit?usp=sharing) to generate the .txt files for the step sequencer, the automated sample playback, and audio effects.

To set up the python environment, open a terminal on your mac computer and enter the following commands:

The very first time:
```
cd /path/to/project/

cd python/lib

python3 -m venv .

source bin/activate

pip install requests
```
all subsequent times:
```
cd /path/to/project/python/lib

source bin/activate

cd everything
```
Now, in order to run the script, enter:
```
python _genAllStepFiles.py
```
This will generate all the relevant files, and save all the old files into an archive folder. A successful run should look like this:
```
(python) bse@bse-mbp everything % python _genAllStepFiles.py
requesting google sheet
moving old sheet to z_old_data.csv
new google sheet downloaded as data.csv
outputting 9 lines to tmp-step-is-manual.txt
outputting 14 lines to tmp-sample-steps.txt
outputting 4 lines to tmp-granulator-steps.txt
outputting 2 lines to tmp-reverb-steps.txt
outputting 18 lines to tmp-step-sequencer-info.txt
  

======== File Line Changes ========
../../step-is-manual.txt  :  9 -> 9 (no change)
../../sample-steps.txt  : 14 -> 14  (no change)
../../granulator-steps.txt  :  4 -> 4 (no change)
../../reverb-steps.txt  :  2 -> 2 (no change)
../../step-sequencer-info.txt : 18 -> 18  (no change)

Confirm overwriting old files? y/n: y
Archived: ../../step-is-manual.txt -> z_old/2025-08-05T02-29-51/step-is-manual.txt
Updated:  ../../step-is-manual.txt
Archived: ../../sample-steps.txt -> z_old/2025-08-05T02-29-51/sample-steps.txt
Updated:  ../../sample-steps.txt
Archived: ../../granulator-steps.txt -> z_old/2025-08-05T02-29-51/granulator-steps.txt
Updated:  ../../granulator-steps.txt
Archived: ../../reverb-steps.txt -> z_old/2025-08-05T02-29-51/reverb-steps.txt
Updated:  ../../reverb-steps.txt
Archived: ../../step-sequencer-info.txt -> z_old/2025-08-05T02-29-51/step-sequencer-info.txt
Updated:  ../../step-sequencer-info.txt

✅ All files updated and old versions archived.
```