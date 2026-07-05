import json
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from urllib.parse import urlparse
from urllib.request import url2pathname

import click

GIT_URL = "git+https://github.com/Aaryan-Kapoor/d2l-cli.git"


def _direct_url():
    """PEP 610 install-origin record, or None for index (PyPI) installs."""
    try:
        raw = distribution("d2l-cli").read_text("direct_url.json")
        return json.loads(raw) if raw else None
    except (PackageNotFoundError, json.JSONDecodeError):
        return None


def _extras():
    try:
        import playwright  # noqa: F401
        return "[login]"
    except ImportError:
        return ""


def _run(cmd):
    click.echo(f"[*] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


@click.command()
@click.option("--ref", help="Git branch or tag to install (default: latest main)")
def update(ref):
    """Update d2l-cli to the latest release from GitHub.

    Works for any install style: a local git checkout is pulled in place,
    anything else is reinstalled from the repo with pip (pipx venvs included).
    """
    info = _direct_url() or {}
    url = info.get("url", "")

    # PEP 610: a local-directory install has a dir_info key (possibly {});
    # index and VCS installs do not.
    if "dir_info" in info and url.startswith("file:"):
        dir_info = info["dir_info"] or {}
        repo = url2pathname(urlparse(url).path)
        code = _run(["git", "-C", repo, "pull", "--ff-only"])
        if code != 0:
            click.echo(
                f"[!] git pull failed in {repo} — resolve local changes and retry.",
                err=True,
            )
            raise SystemExit(code)
        if not dir_info.get("editable"):
            code = _run([sys.executable, "-m", "pip", "install", "--quiet", f"{repo}{_extras()}"])
            if code != 0:
                raise SystemExit(code)
        click.echo("[OK] Updated from local checkout. Run: d2l --version")
        return

    spec = f"d2l-cli{_extras()} @ {GIT_URL}" + (f"@{ref}" if ref else "")
    code = _run([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", spec])
    if code != 0:
        click.echo("[!] Update failed.", err=True)
        raise SystemExit(code)
    click.echo("[OK] Updated. Run: d2l --version")
