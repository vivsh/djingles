
from contextlib import contextmanager
import os
from fabric import task

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


@task
def freeze(c):
    packages = c.run("pip freeze").stdout
    with open(relative_path("requirements.txt"), "w") as fr, \
            open(relative_path("dev_requirements.txt"), "w") as fd:
        for line in packages.splitlines(True):
            name = line.strip().split("=", 1)[0]
            fh = fd if name in DEVELOPMENT_PACKAGES else fr
            fh.write(line)
    c.run("git commit -m 'updated requirements' requirements.txt dev_requirements.txt", warn=True)


@task
def push(c, message=""):
    c.run("git add . --all")
    if message:
        c.run("git commit -am '%s'" % message)
    c.run("git push origin master")


@task
def pypi(c):
    c.run("rm -rf dist/* && python3 setup.py sdist bdist_wheel && twine upload dist/*")


@task
def publish(c, message=""):
    push(c, message)
    pypi(c)