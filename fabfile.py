
from contextlib import contextmanager
import os
from fabric.api import local, run, env, cd, settings, prefix, lcd

BASE_DIR = os.path.realpath(os.path.dirname(__file__))

DEVELOPMENT_PACKAGES = {
    "django_debug_toolbar",
    "devserver",
    "django_extensions",
    "django-ginger-master"
    "fabric"
}


def relative_path(*args):
    return os.path.join(BASE_DIR, *args)


def freeze():
    packages = local("pip freeze", capture=True)
    with open(relative_path("requirements.txt"), "w") as fr, \
            open(relative_path("dev_requirements.txt"), "w") as fd:
        for line in packages.splitlines(True):
            name = line.strip().split("=", 1)[0]
            fh = fd if name in DEVELOPMENT_PACKAGES else fr
            fh.write(line)
    local("git commit -m 'updated requirements' requirements.txt dev_requirements.txt")


def push(message=None):
    local("git add . --all")
    if message:
        with settings(warn_only=True):
            local("git commit -am '%s'" % message)
            # freeze()
    local("git push origin master")


def pypi():
    local("rm -rf dist/* && python3 setup.py sdist bdist_wheel && twine upload dist/*")


def publish(message):
    push(message)
    pypi()