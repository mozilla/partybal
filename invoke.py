#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import partial
import json
import os
from pathlib import Path
import requests
import shutil
import subprocess
from typing import Dict, Iterable, List, Optional

import appdirs
import attr
import cattr
import click
import dateutil.parser
from dateutil.tz import UTC
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pandas as pd

jinja = Environment(loader=FileSystemLoader("."), undefined=StrictUndefined)


class Cache:
    TIMESTAMP_FILENAME = "last_run"
    RESULT_CACHE_PATH = "results"
    EXPERIMENT_BUCKET_URL = "gs://mozanalysis/statistics"
    EXPERIMENTS_FILENAME = "experiments.json"

    def __init__(self, path=None):
        self.path = Path(path or appdirs.user_cache_dir("partybal", "Mozilla"))

    def assert_exists(self, path: Optional[Path] = None):
        (path or self.path).mkdir(parents=True, exist_ok=True)

    def mark_complete(self, date: Optional[str] = None) -> None:
        self.assert_exists()
        (self.path / self.TIMESTAMP_FILENAME).write_text(
            date or datetime.now(UTC).isoformat() + "\n"
        )

    @property
    def last_run(self) -> datetime:
        try:
            return dateutil.parser.isoparse(
                (self.path / self.TIMESTAMP_FILENAME).read_text().strip()
            )
        except Exception:
            return datetime.min.replace(tzinfo=UTC)

    def sync(self, remote_bucket_url=None) -> None:
        self.assert_exists(self.path / self.RESULT_CACHE_PATH)
        result = subprocess.run(
            [
                "gsutil",
                "-m",
                "rsync",
                "-d",
                "-r",
                remote_bucket_url or self.EXPERIMENT_BUCKET_URL,
                str(self.path / self.RESULT_CACHE_PATH),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode:
            raise Exception(result.stdout)

        experiments = cattr.unstructure(ExperimentCollection.from_experimenter())
        (self.path / self.EXPERIMENTS_FILENAME).write_text(json.dumps(experiments))

    def clean(self) -> None:
        shutil.rmtree(self.path)

    def new_since_last_run(self, last_run: Optional[datetime] = None) -> List[Path]:
        last_run = last_run or self.last_run
        results = []
        for p in (self.path / self.RESULT_CACHE_PATH).iterdir():
            mtime = p.stat().st_mtime
            if datetime.fromtimestamp(mtime, UTC) > last_run:
                results.append(p)
        return results

    @property
    def experiments(self) -> "ExperimentCollection":
        serialized = (self.path / self.EXPERIMENTS_FILENAME).read_text()
        deserialized = json.loads(serialized)
        return cattr.structure(deserialized, ExperimentCollection)


## Experimenter API types


@attr.s(auto_attribs=True)
class Variant:
    slug: str
    description: str
    is_control: bool


@attr.s(auto_attribs=True)
class Experiment:
    name: str
    slug: str
    normandy_slug: str
    variants: List[Variant]
    start_date: Optional[int]

    @property
    def branches(self) -> List[str]:
        return sorted(v.slug for v in self.variants)

    @property
    def control_branch_slug(self) -> str:
        for v in self.variants:
            if v.is_control:
                break
        return v.slug

    @property
    def filename_slug(self) -> str:
        return self.normandy_slug.replace("-", "_")

    @property
    def start_date_formatted(self) -> str:
        if not self.start_date:
            return "Never"
        return datetime.fromtimestamp(self.start_date / 1000, UTC).strftime("%Y-%m-%d")

    def render(self, cache_path: Path) -> str:
        results = ResultSet(self.filename_slug, cache_path)
        return jinja.get_template("template.Rmd.jinja2").render(
            experiment=self,
            results=results,
            source_path=str(Path(__file__).parent.resolve()),
            repr=repr,
        )


@attr.s(auto_attribs=True)
class NimbusBranch:
    slug: str


@attr.s(auto_attribs=True)
class NimbusExperiment:
    slug: str
    userFacingName: str
    branches: List[NimbusBranch]
    startDate: Optional[datetime]
    referenceBranch: Optional[str]

    def branches_as_variants(self) -> List[Variant]:
        variants = []
        for branch in self.branches:
            variants.append(
                Variant(
                    slug=branch.slug,
                    description=branch.slug,
                    is_control=branch.slug == self.referenceBranch,
                )
            )
        return variants

    def to_experiment_maybe(self) -> Optional[Experiment]:
        if not self.startDate:
            return None
        return Experiment(
            name=self.userFacingName,
            slug=self.slug,
            normandy_slug=self.slug,
            start_date=int(self.startDate.replace(tzinfo=UTC).timestamp() * 1000),
            variants=self.branches_as_variants(),
        )


cattr.register_structure_hook(
    datetime,
    lambda num, _: datetime.fromisoformat(num.replace("Z", "+00:00")),
)


@attr.s(auto_attribs=True)
class ExperimentCollection:
    EXPERIMENTER_API_URL = (
        "https://experimenter.services.mozilla.com/api/v1/experiments/"
    )

    EXPERIMENTER_NIMBUS_API_URL = (
        "https://experimenter.services.mozilla.com/api/v6/experiments/"
    )

    experiments: Dict[str, Experiment] = {}

    @classmethod
    def from_experimenter(cls):
        l = [
            cattr.structure(e, Experiment)
            for e in requests.get(cls.EXPERIMENTER_API_URL).json()
        ] + [
            cattr.structure(e, NimbusExperiment).to_experiment_maybe()
            for e in requests.get(cls.EXPERIMENTER_NIMBUS_API_URL).json()
        ]
        return cls({x.filename_slug: x for x in l if x})

    def __getitem__(self, item: str) -> Experiment:
        return self.experiments[item]

    def __contains__(self, item: str) -> bool:
        return item in self.experiments


## Result summaries
@attr.s(auto_attribs=True)
class ResultStatistic:
    name: str
    data: pd.DataFrame

    @property
    def comparisons(self) -> List[str]:
        if "comparison" not in self.data.columns:
            return []
        return list(self.data.comparison.fillna("none").unique())


@attr.s(auto_attribs=True)
class ResultMetric:
    name: str
    data: pd.DataFrame

    @property
    def statistics(self) -> Iterable[ResultStatistic]:
        for name, rows in self.data.groupby("statistic"):
            yield ResultStatistic(name, rows)


@attr.s(auto_attribs=True)
class Result:
    path: str
    data: pd.DataFrame

    @classmethod
    def from_path(cls, path) -> "Result":
        data = pd.read_json(path)
        if "comparison" not in data.columns:
            data["comparison"] = "none"
        return cls(path, data)

    @property
    def segments(self) -> List[str]:
        if "segment" not in self.data.columns:
            return ["all"]
        segments = set(self.data.segment.fillna("all").drop_duplicates())
        segments.remove("all")
        l = ["all"] + sorted(segments)
        return l

    @property
    def metrics(self) -> Iterable[ResultMetric]:
        for name, rows in self.data.groupby("metric"):
            yield ResultMetric(name, rows)


@attr.s(auto_attribs=True)
class ResultSet:
    slug: str
    path: Path

    @property
    def overall(self):
        return self.get_result("overall")

    @property
    def weekly(self):
        return self.get_result("weekly")

    @property
    def daily(self):
        return self.get_result("daily")

    @property
    def segments(self):
        for k in ("overall", "weekly", "daily"):
            if not (result := self.get_result(k)):
                continue
            return result.segments
        return []

    def get_result(self, period: str) -> Optional[Result]:
        assert period in ("daily", "weekly", "overall")
        filename = (
            self.path
            / f"{Cache.RESULT_CACHE_PATH}/statistics_{self.slug}_{period}.json"
        )
        if filename.exists():
            return Result.from_path(filename)
        return None

    @property
    def available_code(self):
        try:
            available = []
            if self.overall:
                available.append("O")
            if self.weekly:
                n = len(self.weekly.data.window_index.unique())
                available.append(f"W{n}")
            if self.daily:
                n = len(self.daily.data.window_index.unique())
                available.append(f"D{n}")
            return " ".join(available)
        except Exception:
            return "None"


## Helpers
def slug_from_filename(path: Path) -> Optional[str]:
    if not path.suffix.endswith("json"):
        return None
    return path.name.rsplit("_", 1)[0].split("_", 1)[1]


def render(experiment: Experiment, cache: Cache, output: Path):
    output.mkdir(exist_ok=True)

    slug = experiment.filename_slug
    template = output / (slug + ".Rmd")
    template.write_text(experiment.render(cache.path))

    # Avoid a Conda/Homebrew interaction
    env = dict(os.environ)
    env["R_LIBS_USER"] = ""

    result = subprocess.run(
        [
            "R",
            "--vanilla",
            "-q",
            "-s",
            "-e",
            f"suppressWarnings(rmarkdown::render('{str(template)}', quiet=TRUE))",
        ],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )

    if result.returncode == 0:
        print(f"{slug}: ok")
    else:
        print(f"{slug}: error")
        print(result.stdout)


def render_index(experiments, cache) -> str:
    to_list = {
        slug_from_filename(p)
        for p in cache.new_since_last_run(last_run=datetime.min.replace(tzinfo=UTC))
    }
    to_list.discard(None)
    results = {slug: ResultSet(slug, cache.path) for slug in to_list if slug}
    with_results = [experiments[slug] for slug in to_list if slug in experiments]
    return jinja.get_template("index.html.jinja2").render(
        experiments=with_results,
        results=results,
    )


@click.group()
def cli():
    pass


@cli.command()
@click.option("--output", default="output")
@click.option("--cache")
@click.option(
    "--updated-seconds-ago",
    type=int,
    help="Analyze experiments that were modified in the last X seconds.",
)
@click.option("-j", default=0)
def invoke(output, cache, j, updated_seconds_ago):
    cache = Cache(cache)
    cache.sync()

    last_run = None
    if updated_seconds_ago:
        last_run = datetime.now(UTC) - timedelta(seconds=updated_seconds_ago)

    slugs_to_analyze = {
        slug_from_filename(p) for p in cache.new_since_last_run(last_run)
    }
    slugs_to_analyze.discard(None)

    experiments = cache.experiments

    output = Path(output)
    to_run = [experiments[slug] for slug in slugs_to_analyze if slug in experiments]
    map_function = partial(render, cache=cache, output=output)
    with ThreadPoolExecutor(j or os.cpu_count()) as executor:
        list(executor.map(map_function, to_run))

    (output / "index.html").write_text(render_index(experiments, cache))

    cache.mark_complete()


@cli.command()
@click.option("--cache")
def clean(cache):
    Cache(cache).clean()


@cli.command()
@click.option("--sync/--no-sync")
@click.option("--cache")
@click.option("--output", default="output")
@click.argument("slug", required=False)
def debug(sync, output, slug, cache):
    cache = Cache(cache)
    if sync:
        cache.sync()

    output = Path(output)
    experiments = cache.experiments
    if slug:
        render(experiments[slug], cache, output)
    (output / "index.html").write_text(render_index(experiments, cache))


if __name__ == "__main__":
    cli()
