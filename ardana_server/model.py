from flask import abort, Blueprint, jsonify
import collections
import logging
import os
import re
import time
import yaml

LOG = logging.getLogger(__name__)


MODEL_DIR = os.path.expanduser("~/dev/helion/my_cloud/definition")
CLOUD_CONFIG = "cloudConfig.yml"

bp = Blueprint('model', __name__)

@bp.route("/v2/model")
def get_model():
    try:
        return jsonify(read_model(MODEL_DIR))
    except Exception as e:
        LOG.error(e)
        abort(500)


def get_key_field(obj):
    """
    Several kinds of ids are used in the input model:
        id          : used for servers.yml
        region-name : used for swift/rings.yml
        node_name   : used for baremetalConfig.yml
        name        : all others
    """
    if not obj:
        return None

    for key in ('name', 'id', 'region-name', 'node_name'):
        if key in obj:
            return key


def read_model(model_dir):
    """Reads the input model directory structure into a big dictionary

    Reads all of the yaml files from the given directory and loads them into a
    single giant dictionary.  The dictionary includes tracking information to
    capture where each entry was loaded, so that the object can be written back
    out to the appropriate files
    """

    # First read the top-level cloud config file
    cloud_config_file = os.path.join(model_dir, CLOUD_CONFIG)

    model = {'name': None,
             'version': None,
             'readme': {},
             'fileInfo': {},
             'errors': [],
             }
    with open(cloud_config_file) as f:
        try:
            doc = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.exception("Invalid yaml file")

    if not doc:
        return model

    try:
        model['version'] = doc['product']['version']
    except KeyError:
        raise 'Missing cloud config product version'

    try:
        model['name'] = doc['cloud']['name']
    except KeyError:
        raise 'Cloud config error: no name specified'

    relname = CLOUD_CONFIG
    model['fileInfo'] = {'configFile': cloud_config_file,
                         'directory': model_dir,
                         'files': [ relname ],
                         'sections': collections.defaultdict(list),
                         'fileSectionMap': collections.defaultdict(list),
                         'mtime': os.stat(cloud_config_file).st_mtime,
                         '_object_data': {},
                        }

    # TODO: Move to a function since this is common across all filetypes
    for section, value in doc.iteritems():
        # Capture which section names belong in each file
        model['fileInfo']['sections'][section].append(relname)

        if isinstance(value, list):
            key_field = get_key_field(value[0])
            mapping = {
                    'keyField': key_field,
                    'type': 'array',
                    section: [e[key_field] for e in value],
            }
            model['fileInfo']['fileSectionMap'][relname].append(mapping)

            pass
        elif isinstance(value, dict) and section != 'product':
            # product, which always is the dict {'version':2}, is handled as a
            # primitive
            pass
        else:  # primitive
            model['fileInfo']['fileSectionMap'][relname].append(section)

    yml_re = re.compile(r'\.yml$')
    try:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                if file != CLOUD_CONFIG and yml_re.search(file):
                    relname = os.path.relpath(os.path.join(root, file),
                                              model_dir)
                    model['fileInfo']['files'].append(relname)

    except OSError:
        LOG.warning("Playbooks directory %s doesn't exist. This could indicate"
                    " that the ready_deployment playbook hasn't been run yet. "
                    "The list of playbooks available will be reduced",
                    PLAYBOOKS_DIR)

    return model

def add_to_model():
    pass

def write_model(model_dir):
    pass