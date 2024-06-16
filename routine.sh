#!/bin/bash

source venv/bin/activate

# scrap 
python main.py

# export
python patch_export.py

# commit data.json
git add data.json
git commit -m "auto commit"
git push