#!/usr/bin/env python3

from datetime import datetime
import os
from pathlib import Path
import requests
import shutil
import subprocess
from typing import Dict, List, Optional

import appdirs
import attr
import cattr
import click
import dateutil.parser
from dateutil.tz import UTC
from jinja2 import Environment, FileSystemLoader

jinja = Environment(loader=FileSystemLoader("."))


class Cache:
    TIMESTAMP_FILENAME = "last_run"
    RESULT_CACHE_PATH = "results"
    EXPERIMENT_BUCKET_URL = "gs://mozanalysis"

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
        # avoid a bug on python 3.8
        # https://github.com/GoogleCloudPlatform/gsutil/issues/961
        environ = dict(os.environ)
        environ["CLOUDSDK_GSUTIL_PYTHON"] = "python2.7"
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
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode:
            raise Exception(result.stdout)

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

    @property
    def branches(self) -> List[str]:
        return sorted(v.slug for v in self.variants)

    @property
    def control_branch_slug(self) -> str:
        for v in self.variants:
            if v.is_control:
                break
        return v.slug

    def render(self):
        return jinja.get_template("template.Rmd").render(experiment=self)


@attr.s(auto_attribs=True)
class ExperimentCollection:
    EXPERIMENTER_API_URL = (
        "https://experimenter.services.mozilla.com/api/v1/experiments/"
    )

    experiments: Dict[str, Experiment] = {}

    @classmethod
    def from_experimenter(cls):
        l = [
            cattr.structure(e, Experiment)
            for e in requests.get(cls.EXPERIMENTER_API_URL).json()
        ]
        return cls({x.normandy_slug.replace("-", "_"): x for x in l})

    def __getitem__(self, item: str) -> Experiment:
        return self.experiments[item]


## Result summaries
@attr.s(auto_attribs=True)
class Result:
    pass

@attr.s(auto_attribs=True)
class ResultSet:
    slug: str
    path: Path

    def get_result(self, period: str) -> Optional[Result]:
        assert period in ("daily", "weekly", "overall")
        filename = self.path / f"statistics_{self.slug}_{period}.json"
        if filename.exists():
            return Result(filename)
        return None


## Helpers
def slug_from_filename(path: Path) -> Optional[str]:
    if not path.suffix.endswith("json"):
        return None
    return path.name.rsplit("_", 1)[0].split("_", 1)[1]


def render(experiment: Experiment, path: Path):
    print(experiment.render())


@click.group()
def cli():
    pass


@cli.command()
def invoke():
    cache = Cache()
    cache.sync()
    to_analyze = {slug_from_filename(p) for p in cache.new_since_last_run()}
    to_analyze.discard(None)

    experiments = ExperimentCollection.from_experimenter()

    for slug in to_analyze:
        render(experiments[slug], cache.path)
    cache.mark_complete()


@cli.command()
def clean():
    Cache().clean()


@cli.command()
@click.option("--sync/--no-sync")
@click.argument("slug")
def debug(sync, slug):
    cache = Cache()
    if sync:
        cache.sync()
    render(slug, cache.path)


if __name__ == "__main__":
    cli()
