from ConfigParser import SafeConfigParser
import logging
import os
import sys

LOG = logging.getLogger(__name__)

parser = SafeConfigParser()

default_config = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                               'defaults.cfg'))

config_files = [default_config]
if len(sys.argv) > 1:
    config_files.append(sys.argv[1])

LOG.info("Loading config files %s", config_files)
# This will fail with an exception if the config file cannot be loaded
parser.read(config_files)


def normalize(val):
    # Coerce value to an appropriate python type
    if val.lower() in ("yes", "true"):
        return True

    if val.lower() in ("no", "false"):
        return False

    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            pass

    return val


def get_flask_config():
    """Return all items in the [flask] section.

    The keys are converted to upercase as required by flask.  Since
    SafeConfigParser returns all values as strings
    """
    return {k.upper(): normalize(v) for k, v in parser.items('flask')}


def get(*args, **argv):
    return normalize(parser.get(*args, **argv))


def get_dir(dir_name):
    path = parser.get('paths', dir_name)

    # Relative paths are resolved relative to the top-level directory
    if not path.startswith('/'):
        top_dir = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                ".."))
        path = os.path.abspath(os.path.join(top_dir, path))

    return path
