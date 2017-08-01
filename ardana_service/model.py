import collections
import copy
from flask import abort
from flask import Blueprint
from flask import jsonify
from flask import request
import logging
import os
import random
import yaml

import config.config as config

LOG = logging.getLogger(__name__)

MODEL_DIR = config.get_dir("model_dir")

CLOUD_CONFIG = "cloudConfig.yml"

bp = Blueprint('model', __name__)

# Define some constants to avoid problems caused by typos
CHANGED = 'changed'
IGNORED = 'ignored'
DELETED = 'deleted'
ADDED = 'added'

PASS_THROUGH = 'pass-through'


@bp.route("/api/v2/model", methods=['GET', 'POST'])
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
            write_model(model, MODEL_DIR)
        except Exception as e:
            LOG.exception(e)
            abort(500)
        return 'Success'


@bp.route("/api/v2/model/is_encrypted", methods=['GET'])
def get_encrypted():
    return jsonify({"isEncrypted": False})


@bp.route("/api/v2/model/entities", methods=['GET'])
def get_all_entities():
    return 'Success'


@bp.route("/api/v2/model/entities/<entity>", methods=['GET', 'POST', 'PUT'])
def whole_entity(entity):
    return 'Success'


@bp.route("/api/v2/model/entities/<entity>/<id>",
          methods=['DELETE', 'GET', 'PUT'])
def entry(entity, id):
    return 'Success'


@bp.route("/api/v2/model/files", methods=['GET'])
def get_all_files():

    file_list = []

    # Now read and process all yml files in the dir tree below
    for root, dirs, files in os.walk(MODEL_DIR):
        for file in files:
            relname = os.path.relpath(os.path.join(root, file), MODEL_DIR)
            if file.endswith('.yml'):

                # For now, the description will be just use the filename
                # (without extension) using space in place of underscores
                description = os.path.basename(relname).split('.')[0]
                description = description.replace('_', ' ')

                file_list.append({
                    'name': relname,
                    'description': description
                })

    return jsonify(file_list)


@bp.route("/api/v2/model/files/<path:name>", methods=['GET', 'POST'])
def model_file(name):

    if request.method == 'GET':
        filename = os.path.join(MODEL_DIR, name)
        try:
            with open(filename) as f:
                lines = f.readlines()
            contents = ''.join(lines)

        except IOError:
            pass

        return jsonify(contents)
    else:
        data = request.get_json()

        # Verify that it is valid yaml before accepting it
        try:
            yaml.safe_load(data)
        except yaml.YAMLError:
            LOG.exception("Invalid yaml data")
            abort(400)

        # It's valid, so write it out
        filename = os.path.join(MODEL_DIR, name)
        try:
            with open(filename, "w") as f:
                f.write(data)
            return 'Success'
        except Exception:
            abort(500)


def get_key_field(obj):

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
            raise
        except IOError:
            LOG.exception("Unable to read yaml file")
            raise

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
            filename = os.path.join(root, file)
            if file.endswith('.yml'):
                model['fileInfo']['files'].append(relname)
                with open(filename) as f:
                    try:
                        doc = yaml.safe_load(f)
                        add_doc_to_model(model, doc, relname)
                    except yaml.YAMLError:
                        LOG.exception("Invalid yaml file")

            elif file.startswith('README'):
                ext = file[7:]
                with open(filename) as f:
                    lines = f.readlines()
                model['readme'][ext] = ''.join(lines)

    # Update metadata related to pass-through, if necessary
    update_pass_through(model)

    return model


def add_doc_to_model(model, doc, relname):

    for section, value in doc.iteritems():
        # Add to fileInfo / sections
        model['fileInfo']['sections'][section].append(relname)

        if isinstance(value, list):
            # Add to fileInfo / fileSectionMap
            key_field = get_key_field(value[0])
            mapping = {
                'keyField': key_field,
                'type': 'array',
                section: [e[key_field] for e in value],
            }
            model['fileInfo']['fileSectionMap'][relname].append(mapping)

            # Add to inputModel
            if section not in model['inputModel']:
                model['inputModel'][section] = []
            model['inputModel'][section].extend(value)

        elif isinstance(value, dict) and section == PASS_THROUGH:
            key_fields = []
            if section not in model['inputModel']:
                model['inputModel'][section] = {}

            for key, val in value.iteritems():

                # if pass-through section contains a nested dictionary, add
                #    each of the keys of that nested dict
                if isinstance(val, dict):
                    key_fields.extend([".".join((key, n)) for n in val.keys()])
                    if key not in model['inputModel'][section]:
                        model['inputModel'][section][key] = {}
                    model['inputModel'][section][key].update(val)
                else:
                    key_fields.append(key)
                    model['inputModel'][section][key] = val

            mapping = {
                PASS_THROUGH: key_fields,
                'type': 'object'
            }
            model['fileInfo']['fileSectionMap'][relname].append(mapping)
        else:
            # primitive, or some dict other than pass-through.
            model['fileInfo']['fileSectionMap'][relname].append(section)
            model['inputModel'][section] = value


def update_pass_through(model):

    # If there is only one file containing pass-through data, then its
    # entry in fileInfo / fileSectionMap should be stripped of its nested keys
    # and become a simple string

    if len(model['fileInfo']['sections'][PASS_THROUGH]) == 1:
        filename = model['fileInfo']['sections'][PASS_THROUGH][0]

        for i, val in enumerate(model['fileInfo']['fileSectionMap'][filename]):
            if isinstance(val, dict) and PASS_THROUGH in val:
                model['fileInfo']['fileSectionMap'][filename][i] = \
                    PASS_THROUGH
                break


#
# Functions to write the model
#

# This function is long and should be modularized
def write_model(in_model, model_dir, dry_run=False):  # noqa: C901

    # Create a deep copy of the model to avoid munging the model that was
    # passed in
    model = copy.deepcopy(in_model)

    # Keep track of what was written, by creating a dict with this format:
    #    filename: {
    #        data: <data written to file>
    #        status: DELETED | CHANGED | ADDED | IGNORED
    #    }
    # This is mostly used for unit testing (too return what has changed), but
    # some of this information is also used to detect whether a stale file
    # is lingering in the model dir and that needs to be removed
    written_files = {}

    # Write portion of input model that correspond to existing files
    file_section_map = model['fileInfo']['fileSectionMap']
    for filename, sections in file_section_map.iteritems():
        new_content = {}

        # sections is a list of sections in the file
        for section in sections:

            if isinstance(section, basestring):
                # Skip the remaining processing if the entire section has been
                # removed
                if section not in model['inputModel']:
                    continue

                # This section is just a flat name so the section is just the
                # name.  Note that this will process primitive types as well as
                # single-file pass-through's (which contain no details in the
                # map)
                section_name = section

                if section_name == 'product':
                    new_content[section_name] = \
                        model['inputModel'][section_name]
                else:
                    new_content[section_name] = \
                        model['inputModel'].pop(section_name)
            else:
                # This is a dict that either defines an array (i.e. list)
                #   {'type' : 'array'  <-
                #    'keyField' : 'id' (or 'region-name' or 'name', etc.
                #    '<NAME>': [ '<id1>', '<id2>' ]}
                #    where <NAME> is the section name (e.g. disk-models), and
                #    the value of that entry is a list of ids
                #
                # or it contains an entry (i.e. dict) for pass-through:
                #   {'type' : 'object'
                #    'pass-through': ['k1.k2', 'k1.k3', 'k4']   <- dotted keys
                #   }

                section_type = section['type']
                section_name = [k for k in section.keys()
                                if k not in ('type', 'keyField')][0]

                # Skip the remaining processing if the entire section has been
                # removed
                if section_name not in model['inputModel']:
                    continue

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
                        key_field = section.get('keyField')

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
                    inputPassThru = model['inputModel'].get(PASS_THROUGH)
                    if not inputPassThru:
                        continue

                    # Pass-throughs that are spread across multiple files
                    for dotted_key in section[PASS_THROUGH]:
                        key_list = dotted_key.split('.')

                        if len(key_list) == 1:
                            # There was no dot, so copy the whole dict over
                            key = key_list[0]

                            if key in inputPassThru:
                                val = inputPassThru.pop(key)

                            if PASS_THROUGH not in new_content:
                                new_content[PASS_THROUGH] = {}
                            new_content[PASS_THROUGH][key] = val
                        else:
                            # There was a dot, so there is a nested dict,
                            # so we have to update any existing one
                            (first, second) = key_list

                            # A try is needed in case first is not in input
                            # model
                            try:
                                if second in inputPassThru[first]:
                                    val = inputPassThru[first].pop(second)

                                    if PASS_THROUGH not in new_content:
                                        new_content[PASS_THROUGH] = {}
                                    if first not in new_content[PASS_THROUGH]:
                                        new_content[PASS_THROUGH][first] = {}

                                    new_content[PASS_THROUGH][first][second] \
                                        = val

                                # Remove the dictionary if it is now empty
                                if not inputPassThru[first]:
                                    inputPassThru.pop(first)

                            except (TypeError, KeyError):
                                pass

        real_keys = [k for k in new_content.keys() if k != 'product']
        if real_keys:
            status = write_file(model_dir, filename, new_content, dry_run)
            written_files[filename] = {'data': new_content, 'status': status}

    # Write portion of input model that remain -- these have not been written
    # to any file
    for section_name, contents in model['inputModel'].iteritems():
        # Skip those sections that have been entirely written and removed
        if not contents:
            continue

        # Skip the special 'product' section
        if section_name == 'product':
            continue

        data = {'product': model['inputModel']['product']}

        basename = os.path.join('data', section_name.replace('-', '_'))

        if section_name not in model['fileInfo']['sections']:
            # brand new section
            filename = basename + '.yml'

            data[section_name] = contents
            status = write_file(model_dir, filename, data, dry_run)
            written_files[filename] = {'data': data, 'status': status}

        elif isinstance(contents, list):

            key_field = get_section_key_field(model, section_name)
            if is_split_into_equal_number_of_files(model, section_name):
                # each entry in the list should be written to a separate file,
                # so create new files for each section
                for elt in contents:
                    data[section_name] = [elt]

                    filename = "%s_%s.yml" % (basename, elt[key_field])
                    status = write_file(model_dir, filename, data, dry_run)
                    written_files[filename] = {'data': data, 'status': status}
            else:
                # place all elements of the list into a single file
                data[section_name] = contents
                filename = "%s_%s.yml" % (basename,
                                          contents[0][key_field])
                status = write_file(model_dir, filename, data, dry_run)
                written_files[filename] = {'data': data, 'status': status}
        else:
            # Not a list, so therefore it must be pass-through data that did
            # correspond to known any existing passthrough file. All remaining
            # entries should be written to a single file
            data[section_name] = contents
            filename = "%s_%s.yml" % (basename,
                                      '%4x' % random.randrange(2 ** 32))

            status = write_file(model_dir, filename, data, dry_run)
            written_files[filename] = {'data': data, 'status': status}

    # Remove any existing files in the output directory that are obsolete
    removed = remove_obsolete_files(model_dir, written_files.keys(), dry_run)
    for filename in removed:
        written_files[filename] = {'data': None, 'status': DELETED}

    return written_files


def is_split_into_equal_number_of_files(model, section_name):

    # Count the entries in the fileSectionMap that contain only one
    # instance of the given section

    file_section_map = model['fileInfo']['fileSectionMap']
    for sections in file_section_map.values():
        for section in sections:
            if isinstance(section, dict) and section_name in section:
                id_list = section[section_name]
                if len(id_list) != 1:
                    return

    return True


def get_section_key_field(model, section_name):

    # Find a file that contains the given section and get its key field
    file_section_map = model['fileInfo']['fileSectionMap']
    for filename, sections in file_section_map.iteritems():
        for section in sections:
            try:
                if section_name in section:
                    return section['keyField']
            except (TypeError, KeyError, AttributeError):
                pass


def write_file(model_dir, filename, new_content, dry_run):

    filepath = os.path.join(model_dir, filename)

    parent_dir = os.path.dirname(filepath)
    if not os.access(parent_dir, os.R_OK):
        if not dry_run:
            os.makedirs(parent_dir)

    old_content = {}
    existed = False
    try:
        if os.access(filepath, os.R_OK):
            existed = True
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
        return IGNORED
    else:
        LOG.info("Writing file %s", filename)
        if not dry_run:
            with open(filepath, "w") as f:
                yaml.safe_dump(new_content, f,
                               indent=2,
                               default_flow_style=False,
                               canonical=False)

    # Return an indication of whether a file was written (vs ignored)
    status = CHANGED if existed else ADDED
    return status


def remove_obsolete_files(model_dir, keepers, dry_run):

    # Report which files were deleted
    removed = []

    # Remove any yml files that are no longer relevant, i.e. not in keepers
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            fullname = os.path.join(root, file)
            relname = os.path.relpath(fullname, model_dir)
            if file.endswith('.yml'):
                if relname not in keepers:
                    LOG.info("Deleting obsolete file %s", fullname)
                    if not dry_run:
                        os.unlink(fullname)
                    removed.append(relname)

    return removed
