from __future__ import absolute_import

import logging
import os

from pip.basecommand import Command
from pip.utils import get_recursive_dependencies, get_dependency_graph
from pip._vendor import pkg_resources


logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """Show information about one or more installed packages."""
    name = 'show'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Show information about installed packages.'

    def __init__(self, *args, **kw):
        super(ShowCommand, self).__init__(*args, **kw)
        self.cmd_opts.add_option(
            '-f', '--files',
            dest='files',
            action='store_true',
            default=False,
            help='Show the full list of installed files for each package.')

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return
        query = args

        results = search_packages_info(query)
        print_results(results, options.files)


def search_packages_info(query):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed = dict(
        [(p.project_name.lower(), p) for p in pkg_resources.working_set])
    query_names = [name.lower() for name in query]
    for dist in [installed[pkg] for pkg in query_names if pkg in installed]:
        package = {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'requires': [dep.project_name for dep in dist.requires()],
        }
        file_list = None
        if isinstance(dist, pkg_resources.DistInfoDistribution):
            # RECORDs should be part of .dist-info metadatas
            if dist.has_metadata('RECORD'):
                lines = dist.get_metadata_lines('RECORD')
                paths = [l.split(',')[0] for l in lines]
                paths = [os.path.join(dist.location, p) for p in paths]
                file_list = [os.path.relpath(p, dist.location) for p in paths]
        else:
            # Otherwise use pip's log for .egg-info's
            if dist.has_metadata('installed-files.txt'):
                paths = dist.get_metadata_lines('installed-files.txt')
                paths = [os.path.join(dist.egg_info, p) for p in paths]
                file_list = [os.path.relpath(p, dist.location) for p in paths]

        # use and short-circuit to check for None
        package['files'] = file_list and sorted(file_list)
        yield package


def get_recursive_dep_list(pkg):
    graph = get_dependency_graph(pkg)
    items = []
    maxlen = max([len(p) for p, v in graph.items() if v])

    for p, v in sorted(graph.items()):
        if v:
            items.append(('    %-' + str(maxlen + 2) + 's => %s')
                         % (p, ', '.join(v)))

    return '\n'.join(items)


def print_results(distributions, list_all_files):
    """
    Print the informations from installed distributions found.
    """
    for dist in distributions:
        logger.info("---")
        logger.info("Name: %s" % dist['name'])
        logger.info("Version: %s" % dist['version'])
        logger.info("Location: %s" % dist['location'])
        logger.info("Requires: %s" % ', '.join(dist['requires']))
        logger.info("Requires recursive:\n%s",
                    get_recursive_dep_list(dist['name']))
        if list_all_files:
            logger.info("Files:")
            if dist['files'] is not None:
                for line in dist['files']:
                    logger.info("  %s" % line.strip())
            else:
                logger.info("Cannot locate installed-files.txt")
