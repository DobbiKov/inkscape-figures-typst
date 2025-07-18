#!/usr/bin/env python3

import time
from logging.handlers import RotatingFileHandler
import os
import re
import logging
import subprocess
import textwrap
import warnings
from pathlib import Path
from shutil import copy
from daemonize import Daemonize
import click
import platform
from inkscapefigures.picker import pick
import pyperclip
from appdirs import user_config_dir
from inkscape_svg_to_typst.typst_inkscape import process_svg

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger('inkscape-figures-typst')
debug_log_path = Path("/Users/dobbikov/Desktop/log.log")
fh = RotatingFileHandler(debug_log_path, maxBytes=2_000_000, backupCount=5)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
log.addHandler(fh)

def inkscape(path):
    with warnings.catch_warnings():
        # leaving a subprocess running after interpreter exit raises a
        # warning in Python3.7+
        warnings.simplefilter("ignore", ResourceWarning)
        subprocess.Popen(['inkscape', str(path)])

def indent(text, indentation=0):
    lines = text.split('\n');
    return '\n'.join(" " * indentation + line for line in lines)

def beautify(name):
    return name.replace('_', ' ').replace('-', ' ').title()





def typst_template(name, title):
    return '\n'.join((
        f"#import \"figures/{name}.typ\":diagram as {name}",
        f"#{name}()"
        ))

# From https://stackoverflow.com/a/67692
def import_file(name, path):
    import importlib.util as util
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load user config

user_dir = Path(user_config_dir("inkscape-figures-typst", "Castel"))

if not user_dir.is_dir():
    user_dir.mkdir()

roots_file =  user_dir / 'roots'
template = user_dir / 'template.svg'
config = user_dir / 'config.py'

if not roots_file.is_file():
    roots_file.touch()

if not template.is_file():
    source = str(Path(__file__).parent / 'template.svg')
    destination = str(template)
    copy(source, destination)

if config.exists():
    config_module = import_file('config', config)
    typst_template = config_module.typst_template


def add_root(path):
    path = str(path)
    roots = get_roots()
    if path in roots:
        return None

    roots.append(path)
    roots_file.write_text('\n'.join(roots))


def get_roots():
    return [root for root in roots_file.read_text().split('\n') if root != '']


@click.group()
def cli():
    pass


@cli.command()
@click.option('--daemon/--no-daemon', default=True)
def watch(daemon):
    """
    Watches for figures.
    """
    if platform.system() == 'Linux':
        watcher_cmd = watch_daemon_inotify
    else:
        watcher_cmd = watch_daemon_fswatch

    if daemon:
        temp_app = ""
        daemon = Daemonize(app='inkscape-figures-typst',
                           pid='/tmp/inkscape-figures-typst.pid',
                           action=watcher_cmd)
        daemon.start()
        log.info("Watching figures.")
    else:
        log.info("Watching figures.")
        watcher_cmd()


def maybe_recompile_figure(filepath):
    filepath = Path(filepath)
    # A file has changed
    if filepath.suffix != '.svg':
        log.debug('File has changed, but is nog an svg {}'.format(
            filepath.suffix))
        return

    log.info('Recompiling %s', filepath)

    # csv_path = filepath.parent / (filepath.stem + '.csv')
    csv_path = filepath
    name = filepath.stem

    inkscape_version = subprocess.check_output(['inkscape', '--version'], universal_newlines=True)
    log.debug(inkscape_version)

    # Convert
    # - 'Inkscape 0.92.4 (unknown)' to [0, 92, 4]
    # - 'Inkscape 1.1-dev (3a9df5bcce, 2020-03-18)' to [1, 1]
    # - 'Inkscape 1.0rc1' to [1, 0]
    inkscape_version = re.findall(r'[0-9.]+', inkscape_version)[0]
    inkscape_version_number = [int(part) for part in inkscape_version.split('.')]

    # Right-pad the array with zeros (so [1, 1] becomes [1, 1, 0])
    inkscape_version_number= inkscape_version_number + [0] * (3 - len(inkscape_version_number))

    log.info('Running command:')

    # Recompile the svg file
    try:
        process_svg(csv_path)
    except Exception:
        pass


    # Copy the LaTeX code to include the file to the clipboard
    template = typst_template(name, beautify(name))
    pyperclip.copy(template)
    log.info('Copying typst template:')
    log.info(textwrap.indent(template, '    '))

def watch_daemon_inotify():
    import inotify.adapters
    from inotify.constants import IN_CLOSE_WRITE

    while True:
        roots = get_roots()

        # Watch the file with contains the paths to watch
        # When this file changes, we update the watches.
        i = inotify.adapters.Inotify()
        i.add_watch(str(roots_file), mask=IN_CLOSE_WRITE)

        # Watch the actual figure directories
        log.info('Watching directories: ' + ', '.join(get_roots()))
        for root in roots:
            try:
                i.add_watch(root, mask=IN_CLOSE_WRITE)
            except Exception:
                log.debug('Could not add root %s', root)

        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event

            # If the file containing figure roots has changes, update the
            # watches
            if path == str(roots_file):
                log.info('The roots file has been updated. Updating watches.')
                for root in roots:
                    try:
                        i.remove_watch(root)
                        log.debug('Removed root %s', root)
                    except Exception:
                        log.debug('Could not remove root %s', root)
                # Break out of the loop, setting up new watches.
                break

            # A file has changed
            path = Path(path) / filename
            maybe_recompile_figure(path)


def watch_daemon_fswatch():
    while True:
        roots = get_roots()
        log.info('Watching directories: ' + ', '.join(roots))
        # Watch the figures directories, as weel as the config directory
        # containing the roots file (file containing the figures to the figure
        # directories to watch). If the latter changes, restart the watches.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            p = subprocess.Popen(
                    ['fswatch', *roots, str(user_dir)], stdout=subprocess.PIPE,
                    universal_newlines=True)

        while True:
            filepath = p.stdout.readline().strip()

            # If the file containing figure roots has changes, update the
            # watches
            if filepath == str(roots_file):
                log.info('The roots file has been updated. Updating watches.')
                p.terminate()
                log.debug('Removed main watch %s')
                break
            if "_dobb_clean" in filepath:
                continue
            maybe_recompile_figure(filepath)



@cli.command()
@click.argument('title')
@click.argument(
    'root',
    default=os.getcwd(),
    type=click.Path(exists=False, file_okay=False, dir_okay=True)
)
def create(title, root):
    """
    Creates a figure.

    First argument is the title of the figure
    Second argument is the figure directory.

    """
    title = title.strip()
    file_name = title.replace(' ', '-').lower() + '.svg'
    figures = Path(root).absolute()
    if not figures.exists():
        figures.mkdir()

    figure_path = figures / file_name

    # If a file with this name already exists, append a '2'.
    if figure_path.exists():
        print(title + ' 2')
        return

    copy(str(template), str(figure_path))
    add_root(figures)
    inkscape(figure_path)

    # Print the code for including the figure to stdout.
    # Copy the indentation of the input.
    leading_spaces = len(title) - len(title.lstrip())
    print(indent(typst_template(figure_path.stem, title), indentation=leading_spaces))

@cli.command()
@click.argument(
    'root',
    default=os.getcwd(),
    type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
def edit(root):
    """
    Edits a figure.

    First argument is the figure directory.
    """

    figures = Path(root).absolute()

    # Find svg files and sort them
    files = figures.glob('*.svg')
    files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

    # Open a selection dialog using a gui picker like rofi
    names = [beautify(f.stem) for f in files]
    _, index, selected = pick(names)
    if selected:
        path = files[index]
        add_root(figures)
        inkscape(path)

        # Copy the LaTeX code to include the file to the clipboard
        template = typst_template(path.stem, beautify(path.stem))
        pyperclip.copy(template)
        log.debug('Copying Typst template:')
        log.debug(textwrap.indent(template, '    '))

@cli.command()
def testwatch():
    watch_daemon_fswatch()

if __name__ == '__main__':
    # maybe_recompile_figure("/Users/dobbikov/Desktop/typst/test_notes/figures/test-fig.svg")
    cli()
    # watch_daemon_fswatch()
