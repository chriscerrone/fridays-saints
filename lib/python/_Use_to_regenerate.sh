#!/bin/bash
cd "$(dirname "$0")"
source bin/activate 
cd everything
python _genAllStepFiles.py