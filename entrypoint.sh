#!/bin/bash
set -euxo pipefail
export PATH=/opt/conda/envs/partybal/bin:$PATH
/opt/conda/envs/partybal/bin/python /app/invoke.py "$@"
/opt/conda/envs/partybal/bin/gsutil -m rsync -r ${OUTPUT}/ $BUCKET_URL
