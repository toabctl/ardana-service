from flask import abort, Blueprint, jsonify
import collections
import logging
import os
import re
import yaml

LOG = logging.getLogger(__name__)

# os.path.expanduser("~/dev/helion/my_cloud/definition")
MODEL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..',
                             'model'))

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
        except yaml.YAMLError:
            LOG.exception("Invalid yaml file")

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
    model['fileInfo'] = {
        'configFile': cloud_config_file,
        'directory': model_dir,
        'files': [relname],
        'sections': collections.defaultdict(list),
        'fileSectionMap': collections.defaultdict(list),
        'mtime': os.stat(cloud_config_file).st_mtime,
        '_object_data': collections.defaultdict(list),
    }
    model['inputModel'] = {}

    add_to_model(model, doc, relname)

    yml_re = re.compile(r'\.yml$')
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            # avoid processing top-leve cloud config again
            if file == CLOUD_CONFIG:
                continue

            relname = os.path.relpath(os.path.join(root, file), model_dir)
            if yml_re.search(file):
                model['fileInfo']['files'].append(relname)
            elif file.startswith('README'):
                ext = file[7:]
                with open(file) as f:
                    lines = f.readlines()
                model['readme'][ext] = ''.join(lines)

            filename = os.path.join(root, file)
            with open(filename) as f:
                try:
                    doc = yaml.safe_load(f)
                    add_to_model(model, doc, relname)
                except yaml.YAMLError:
                    LOG.exception("Invalid yaml file")

    update_objects(model)
    del model['fileInfo']['_object_data']

    return model


def add_to_model(model, doc, relname):

    index = 0
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

        elif isinstance(value, dict) and section != 'product':
            # product, which always is the dict {'version':2}, is handled as a
            # primitive
            # Track where objects are, but don't add them to the fileSectionMap
            # yet
            obj = {'index': index,
                   'file': relname,
                   'data': value}
            model['fileInfo']['_object_data'][section].append(obj)
            index += 1

        else:  # primitive or product
            model['fileInfo']['fileSectionMap'][relname].append(section)

        if isinstance(value, list):
            if section not in model['inputModel']:
                model['inputModel'][section] = []
            model['inputModel'][section].extend(value)
        else:
            if section not in model['inputModel']:
                model['inputModel'][section] = {}
            model['inputModel'][section].update(value)


def update_objects(model):
    """
    Update fileSectionMaps for files that contain an objects section
    """
    for section, obj_list in model['fileInfo']['_object_data'].iteritems():
        if len(obj_list) > 1:
            # pass-through is the only section supported in multiple files
            if section != 'pass-through':
                raise Exception('The section %s has been found in multiple '
                                'files, which is not currently supported' %
                                section)

            # FIXME(gary): Handling pass-through sections is borked.  This has
            # to be tested with one of the models that has them
            for obj in obj_list:
                relname = obj['file']

                mapping = {
                    'type': 'object',
                }
                model['fileInfo']['fileSectionMap'][relname].append(mapping)
        else:
            relname = obj_list[0]['file']
            index = obj_list[0]['index']
            model['fileInfo']['fileSectionMap'][relname].insert(index, section)


def write_model(model_dir):
    pass
