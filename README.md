# party balloon

it's like a pilot balloon, but unserious.

![](jan_erichsen.jpg)

# invocation

`python invoke.py invoke --output ./output -j 4` will run all experiments that have changed since the last run, using 4 R invocations at once. If `j` is not specified, partybal will run in parallel by default, starting as many threads as you have processors. The resulting HTML will be stored in `./output/`.

# what _on earth_ is going on here

Partybal creates a static website that serves as a proof-of-existence for statistics from [Jetstream](https://github.com/mozilla/jetstream).

Basically what happens, what happens is:

* invoke.py downloads the experiment results from GCS
* invoke.py uses the contents of the results and `template.Rmd.jinja2` to generate an RMarkdown document for each experiment that's changed since its last run (or since `--updated-seconds-ago`).
* invoke.py shells out to R to build each experiment's RMarkdown notebook to HTML

`plot_functions.R` has a function named `plot_X` for each Jetstream statistic `X`, which accepts the arguments `df`, `metric`, `comparison`, `period`, and `segment`.
Partybal will probably break if you add a Statistic to Jetstream and don't add a corresponding `plot_` function here. That would be sad!

The plot_ functions can return anything that knitr knows how to render, but a ggplot grob or a data.frame are good choices.

# environments

Spin up an environment with `conda create -n partybal --file conda-linux-64.lock` (or `-osx` as appropriate)

Update dependencies with `conda update --all`.

Save a new lock file from environment.yml by `pip install`ing conda-lock and running `conda-lock`.

# state

partybal tries not to do more work than it has to.

Partybal will generate a complete TOC after every run but will generate results pages only for the experiments that changed, so if you are not persisting the output path between runs, you should not remove files from GCS that are not present in the local output path when you synchronize it to GCS.

It decides which experiments to run one of two ways:

## memory, turn your face to the moonlight

By default, it remembers when it last ran, and only regenerates pages for experiments that changed since that run.

The path it uses to remember this state is chosen with `appdirs.user_cache_dir("partybal", "Mozilla")` ([docs](https://github.com/ActiveState/appdirs)).

If this path is not persisted between runs, Partybal will always do lots of work.

## since \<seconds\> ago

Alternatively, if you pass `--updated-seconds-ago N`, it will only rebuild experiments that have changed in the last N seconds.
