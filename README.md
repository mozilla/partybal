# party balloon

it's like a pilot balloon, but unserious.

![](jan_erichsen.jpg)

# invocation

`python invoke.py invoke --output ./output -j 4` will run all experiments that have changed since the last run, using 4 R invocations at once. If `j` is not specified, partybal will run in parallel by default, starting as many threads as you have processors. The resulting HTML will be stored in `./output/`.

# environments

Spin up an environment with `conda create -n partybal --file conda-linux-64.lock` (or `-osx` as appropriate)

Save a new lock file from environment.yml by `pip install`ing conda-lock and running `conda-lock`.

# state

partybal tries not to do more work than it has to. It remembers when it last ran, and only regenerates pages for experiments that changed since that run.

The path it uses is chosen with `appdirs.user_cache_dir("partybal", "Mozilla")` ([docs](https://github.com/ActiveState/appdirs)).

If this path is not persisted between runs, Partybal will always do lots of work.

Partybal will generate a complete TOC after every run but will generate results pages only for the experiments that changed, so if you are not persisting the output path between runs, you should not remove files from GCS that are not present in the local output path when you synchronize it to GCS.
