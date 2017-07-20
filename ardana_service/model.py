from flask import abort, Blueprint, jsonify, request
import collections
import copy
import logging
import os
import random
import yaml

LOG = logging.getLogger(__name__)

# MODEL_DIR = os.path.expanduser("~/dev/helion/my_cloud/definition")
MODEL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                             '..', 'model'))

NEW_MODEL_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                 '..', 'model2'))

CLOUD_CONFIG = "cloudConfig.yml"

bp = Blueprint('model', __name__)


@bp.route("/v2/model", methods=['GET', 'POST'])
def model():
    if request.method == 'GET':
        try:
            return jsonify(read_model(MODEL_DIR))
        except Exception as e:
            LOG.exception(e)
            abort(500)

    else:
        model = request.get_json() or {}
        try:
            write_model(model, NEW_MODEL_DIR)
        except Exception as e:
            LOG.exception(e)
            abort(500)
        return 'Success'


def get_key_field(obj):
    #
    # Several kinds of ids are used in the input model:
    #     id          : used for servers.yml
    #     region-name : used for swift/rings.yml
    #     node_name   : used for baremetalConfig.yml
    #     name        : all others
    # Figure out which one is populated and return it
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
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            # avoid processing top-level cloud config again
            if file == CLOUD_CONFIG:
                continue

            relname = os.path.relpath(os.path.join(root, file), model_dir)
            if file.endswith('.yml'):
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

    # Update fileSectionMaps for files that contain an objects section
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

    # Create a deep copy of the model
    model = copy.deepcopy(model)

    written_files = []

    # Write portion of input model that correspond to existing files
    file_section_map = model['fileInfo']['fileSectionMap']
    for filename, sections in file_section_map.iteritems():
        new_content = {}

        # sections is a list of sections in the file
        for section in sections:
            if isinstance(section, basestring):
                # This section is just a flat name, like 'product',
                # so get its value directly from the inputModel section
                new_content[section] = model['inputModel'][section]
            else:
                # This is a dict that either contains an entry
                #   {'type' : 'object'
                #    '<NAME>': {someobject} }
                # or it contains
                #   {'type' : 'array'
                #    'keyField' : 'id' (or 'region-name' or 'name', etc.
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
                        new_content[section_name] = \
                            model['inputModel'].pop(section_name)

                    else:
                        # This section of the input model is contained in a
                        # several files.  Write out just the portions that
                        # belong in this file

                        # Get the list of ids for this file
                        our_ids = section[section_name]

                        for model_item in model['inputModel'][section_name]:
                            id = model_item.get(key_field)
                            if id in our_ids:
                                if section_name not in new_content:
                                    new_content[section_name] = []
                                new_content[section_name].append(model_item)

                        # Remove these from the model
                        model['inputModel'][section_name] = \
                            [k for k in model['inputModel'][section_name]
                             if k[key_field] not in our_ids]

                else:
                    # Handle section_type == 'object'
                    pass

        real_keys = [k for k in new_content.keys() if k != 'product']
        if real_keys:
            write_file(model_dir, filename, new_content)
            written_files.append(filename)

    # Write portion of input model that remain -- these have not been written
    # to any file
    for section_name, contents in model['inputModel'].iteritems():
        # Skip those sections that have been entirely written
        if not contents:
            continue

        # Skip the special 'product' section
        if section_name == 'product':
            continue

        # TODO(gary): the old code had logic for suppressing objects other than
        #   PASS_THROUGH.  Not sure if that is needed

        data = {
            'product': model['inputModel']['product'],
        }

        basename = section_name.replace('-', '_') + '.yml'

        if section_name not in model['fileInfo']['sections']:
            # brand new section
            filename = os.path.join('data', basename + '.yml')

            # TODO(gary): the old code had logic for extracting array
            #             elements when contents was an array
            data[section_name] = contents
            write_file(model_dir, filename, data)
        else:
            # Count the entries in the fileSectionMap that contain only one
            # instance of the given section
            file_section_map = model['fileInfo']['fileSectionMap']
            count = 0
            for sections in file_section_map.values():
                for section in sections:
                    try:
                        if len(section.get(section_name, [])) == 1:
                            count += 1
                    except TypeError:
                        pass

            # TODO(ary): set the data field
            if isinstance(contents, list):
                key_field = get_section_key_field(model, section_name)
                if count == len(contents):
                    # each element has its own file, so create new files
                    # for each section
                    for elt in contents:
                        data[section_name] = [elt]

                        filename = "%s_%s.yml" % (basename,
                                                  elt[key_field])
                        write_file(model_dir, filename, data)
                else:
                    # place all elements into a single file
                    filename = "%s_%s.yml" % (basename,
                                              contents[0][key_field])
                    write_file(model_dir, filename, data)
            else:
                # not a list: write to a new file
                name = section_name.replace('-', '_')
                name += '%4x' % random.randrange(2 ** 32) + ".yml"

                write_file(model_dir, filename, data)

    # Remove any existing files in the output directory that are obsolete
    remove_obsolete(model_dir, written_files)


def get_section_key_field(model, section_name):

    # Find a file that contains the given section and get its key field
    file_section_map = model['fileInfo']['fileSectionMap']
    for filename, sections in file_section_map.iteritems():
        for section in sections:
            try:
                if section_name in section:
                    return section['key_field']
            except TypeError:
                pass


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
        LOG.info("Ignoring unchanged file %s", filename)
    else:
        LOG.info("Writing file %s", filename)
        with open(filepath, "w") as f:
            yaml.safe_dump(new_content, f,
                           indent=2,
                           default_flow_style=False,
                           canonical=False)

    # TODO(gary): consider writing old files to backup dir


def remove_obsolete(model_dir, keepers):

    # Remove any yml files that are no longer relevant, i.e. not in keepers
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            fullname = os.path.join(root, file)
            relname = os.path.relpath(fullname, model_dir)
            if file.endswith('.yml'):
                if relname not in keepers:
                    LOG.info("Deleting obsolete file %s", fullname)
                    os.unlink(fullname)
