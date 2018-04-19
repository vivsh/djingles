
import jinja2
import os
import getpass
import shutil
import re
import click
from .main import cli


def read_template(file_name, **ctx):
    file_name = os.path.realpath(os.path.join(__file__, "../templates", file_name))
    with open(file_name) as f:
        template = jinja2.Template(f.read())
        return template.render(**ctx)


@cli.command()
@click.option("--port", type=int, required=True)
@click.option("--host", default="")
@click.option("--http", default=False)
@click.option("--threads", default=10)
@click.option("--processes", default=2)
@click.option("--env", default="")
def uwsgi_conf(port, http, host, threads, processes, env):
    ctx = locals()
    content = read_template("uwsgi.ini", **ctx)
    content = re.sub(r'\n+', '\n', content)
    click.echo(content)


@cli.command()
@click.option("--name", type=str, required=True)
@click.option("--executable", type=click.Path(exists=True, dir_okay=False), help="Path to uwsgi executable", default=lambda : shutil.which("uwsgi"))
@click.option("--conf", type=click.Path(exists=True, dir_okay=False, readable=True), required=True)
@click.option("--dir", type=click.Path(exists=True, file_okay=True), help="Working Directory", default=os.getcwd)
@click.option("--description", type=str)
@click.option("--before", type=str, default="nginx.service")
@click.option("--after", type=str, default="network.target")
@click.option("--user", type=str, default=getpass.getuser)
@click.option("--group", type=str)
def uwsgi_service(name, executable, conf, dir, description, before, after, user, group):
    ctx = locals()
    content = read_template("uwsgi.service", **ctx)
    content = re.sub(r'\n+', '\n', content)
    click.echo(content)


@cli.command()
@click.option("--port", default=80)
@click.option("--server-name", default="_")
@click.option("--static", default=lambda: os.path.realpath(os.path.join(os.getcwd(), "../static")))
@click.option("--media", default=lambda: os.path.realpath(os.path.join(os.getcwd(), "../media")))
@click.option("--uwsgi-port", required=True)
@click.option("--default", default=True)
def nginx_conf(port, server_name, static, media, uwsgi_port, default):
    ctx = locals()
    content = read_template("nginx.conf", **ctx)
    content = re.sub(r'\n+', '\n', content)
    click.echo(content)