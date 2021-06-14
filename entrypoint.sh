#!/bin/bash
conda activate partybal
python invoke.py "$@"
gsutil -m rsync -r ${OUTPUT}/ $BUCKET_URL
