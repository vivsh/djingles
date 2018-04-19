
import jinja2
import os
import getpass
import shutil
import re
import click
from .main import cli


def make_dirs(folders):
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


@cli.command()
@click.argument("name")
def start_project(name):
    cwd = os.getcwd()
    src = cwd if os.path.basename(cwd) == "src" else os.path.join(cwd, "src")
    base_dir = os.path.dirname(src)
    make_dirs([os.path.join(base_dir, f) for f in ("src", "etc", "static", "media", "log", "data")])

