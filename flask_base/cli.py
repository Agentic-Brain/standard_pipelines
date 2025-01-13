import click
from flask.cli import with_appcontext
from .version import get_versions

@click.command('version')
@with_appcontext
def version_command():
    """Display version information."""
    versions = get_versions()
    click.echo(f"Flask Base Framework v{versions['flask_base']}")
    click.echo(f"Application v{versions['app']}")

def init_app(app):
    app.cli.add_command(version_command) 