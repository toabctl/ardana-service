from flask import abort, Blueprint, jsonify, request
import collections
import logging
import os
import re
import yaml

LOG = logging.getLogger(__name__)

MODEL_DIR = os.path.expanduser("~/dev/helion/my_cloud/definition")
MODEL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'model'))

NEW_MODEL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'model2'))

CLOUD_CONFIG = "cloudConfig.yml"

bp = Blueprint('model', __name__)


@bp.route("/v2/model", methods=['GET','POST'])
def model():
    if request.method == 'GET':
        try:
            return jsonify(read_model(MODEL_DIR))
        except Exception as e:
            LOG.error(e)
            abort(500)

    else:
        model = request.get_json() or {}
        try:
            write_model(model, NEW_MODEL_DIR)
        except Exception as e:
            LOG.error(e)
            abort(500)
        return 'Success'


def get_key_field(obj):
    """
    Several kinds of ids are used in the input model:
        id          : used for servers.yml
        region-name : used for swift/rings.yml
        node_name   : used for baremetalConfig.yml
        name        : all others
    Figure out which one is populated and return it
    """
    if obj:
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

    # First read and process the top-level cloud config file
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
        'mtime': int(1000 * os.stat(cloud_config_file).st_mtime),
        '_object_data': collections.defaultdict(list),
    }
    model['inputModel'] = {}

    add_doc_to_model(model, doc, relname)

    # Now read and process all yml files in the dir tree below
    yml_re = re.compile(r'\.yml$')
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            # avoid processing top-level cloud config again
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
                    add_doc_to_model(model, doc, relname)
                except yaml.YAMLError:
                    LOG.exception("Invalid yaml file")

    update_file_section_maps(model)
    del model['fileInfo']['_object_data']

    return model


def add_doc_to_model(model, doc, relname):

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


def update_file_section_maps(model):
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
                    # FIXME{gary): should also have property key
                }
                model['fileInfo']['fileSectionMap'][relname].append(mapping)
        else:
            relname = obj_list[0]['file']
            index = obj_list[0]['index']
            model['fileInfo']['fileSectionMap'][relname].insert(index, section)


# Functions to write the model


def write_model(model, model_dir):

    # keep track of which sections of the input model have been written, in
    # order to detect sections that have not been written (and hence must
    # be new to the input model)
    written = collections.defaultdict(list)
    written_files = []

    ALL = '__all_items_in_section__'

    for filename, contents in model['fileInfo']['fileSectionMap'].iteritems():

        new_content = {}

        # contents is a list of sections in the file
        for section in contents:
            if isinstance(section, basestring):
                # This section is just a flat name, like 'product',
                # so get its value directly from the inputModel section
                new_content[section] = model['inputModel'][section]
                written[section].append(ALL)
            else:
                # This is a dict that either contains an entry
                #   {'type' : 'object'
                #    '<NAME>': {someobject} }
                # or it contains
                #   {'type' : 'array'
                #    'keyField' : 'id' (or 'region-name' or 'name' or 'node_name'
                #    '<NAME>': [ '<id1>', '<id2>' ]}
                #    where <NAME> is the section name (e.g. disk-models), and
                #    the value of that entry is a list of ids
                section_type = section['type']
                key_field = section.get('keyField')
                section_name = [k for k in section.keys()
                                if k not in ('type', 'keyField')][0]

                if section_type == 'array':

                    if len(model['fileInfo']['sections'][section_name]) == 1:
                        # This section of the input model is contained in a
                        # single file, so write out all members of this section 
                        new_content[section_name] = model['inputModel'][section_name]
                        written[section_name].append(ALL)
                    else:
                        # This section of the input model is contained in a
                        # several files.

                        # Get the list of ids
                        ids = section[section_name]

                        for model_item in model['inputModel'][section_name]:
                            if model_item.get(key_field) in ids:
                                written[section_name].append(model_item.get(key_field))
                                if section_name not in new_content:
                                    new_content[section_name] = []
                                new_content[section_name].append(model_item)

                else:
                    # Handle section_type == 'object'
                    pass

        real_keys = [k for k in new_content.keys() if k != 'product']
        if real_keys:
            write_file(model_dir, filename, new_content)
            written_files.append(filename)

    # TODO(gary):
    #    create new files for any sections that have not been written
    #    delete any existing files that are no longer used

def write_file(model_dir, filename, new_content):

    filepath = os.path.join(model_dir, filename)

    parent_dir = os.path.dirname(filepath)
    if not os.access(parent_dir, os.R_OK):
        os.makedirs(parent_dir)

    old_content = {}
    try:
        if os.access(filepath, os.R_OK):
            with open(filepath) as f:
                old_content = yaml.safe_load(f)
    except yaml.YAMLError:
        LOG.exception("Invalid yaml file %s", filepath)
    except IOError as e:
        LOG.error(e)

    # Avoid writing the file if the contents have not changes.  This preserves
    # any comments that may exist in the old file
    if new_content == old_content:
        LOG.info("file %s unchanged", filename)
    else:
        LOG.info("Writing file %s", filename)
        with open(filepath, "w") as f:
            yaml.safe_dump(new_content, f, indent=2, default_flow_style=False, canonical=False)

    # TODO(gary): consider writing old files to backup dir
