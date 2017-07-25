Input Model
===========

Directory Layout
----------------
When stored on disk, the input model is simply one or more files which may be
stored in a nested directory structure.  The one hard requirement is that the
top level must contain the file ``cloudConfig.yml``.

The convention that most input models follow is that ``cloudConfig.yml`` is the
only YAML file at the top level of the tree, and a ``data`` subdirectory
contains all of the other files and nested subdirectories.

There are two types of files:

- a README file 

  This can have an optional suffix, and the file contents are simply loaded
  verbatim

- YAML files

  All other files in the model are formatted as conventional block formatted
  YAML.


File Layout
-----------
All YAML files are expected to be structured at the top level as a dictionary.

There are four types of entries in each dictionary.

Product
~~~~~~~
Each file will contain the following entry::

  product:
    version: 2

Nested Dictionaries
~~~~~~~~~~~~~~~~~~~
Most of the other keys in the dictionary are unique across all files in the
model.  For example, the file ``data/control_plane.yml`` is normally the only
YAML file containing the key ``control-planes``::

   control-planes:
     - name: control-plane-1
       ...

If the entry in the top-level directory in turn a nested dictionary, that key
is required to be unique across the data model (with the special exception
of ``pass-through``, described next).  For example,
``cloudConfig.yml`` contains the entry::

   cloud:
     name: padawan
     ...

and thus no other file in the data model contains a ``cloud`` entry.

Pass-Through
~~~~~~~~~~~~
The exception to the uniqueness of nested dictionaries is the special one whose
key is ``pass-through``.  This particular dictionary may appear in more than one
data model yaml file.  But the uniqueness constraint is pushed down one or two
levels on this item: if ``pass-through`` contains a nested dictionary, either
its key must be unique, or it contains another nested dictionary whose entries
must be unique.  For example, ``pass-through-1.yml`` could contain::

   pass-through:
      global:
         foo: fooey

while ``pass-through-2.yml`` could countain::

   pass-through:
      global:
         bar: baz

since the concatenated sub-key ``global.foo`` is different from ``global.bar``.

Nested Arrays
~~~~~~~~~~~~~
The remaining entries in every dictionary are arrays of dictionaries.  Each
dictionary must have a key field, which is one of: ``name``, ``id``,
``region-name``, ``node_name``.  Most of these top-level dictionary keys appear
in only one file.  For example, the ``firewall-rules`` dictionary normally
appears only in the ``data/firewall_rules.yml`` file.

Some dictionaries can be spread across multiple file, provided that their key
fields are unique.  The most common example of this is disk models.  For
example, in one model, the file ``data/disks_compute.yml`` contains::

   disk-model:
   - name: COMPUTE-DISKS
     ...

while ``data/disk_controller_1TB.yml`` contains::

   disk-model:
   - name: CONTROLLER-1TB-DISKS
     ...


JSON Layout
-----------
The data model used by the REST API is a single JSON structure.  It contains the
contents of all of the files on disk joined together into a single structure.
It contains metadata that ....

Returned by API

The input model::

  {
    "fileInfo": {        # Metadata section
        "fileSectionMap": {       # which files contain which data
            "cloudConfig.yml": [
                "product",
                "cloud"
            ],
        "files": [                # Simple list of files
           "cloudConfig.yml",
           ...
        ],
        "sections": {             # List of top
            "cloud": [
                "cloudConfig.yml"
            ],
            ...
        }

       
    },
    "inputModel": {      # Data section
                        
    }
    
Metadata
~~~~~~~~
# TODO: Add example of a list in the fileSectionMap

Input model:

Most sections are an list of dictionaries, for example:objects::

        "networks": [
                {
                    "cidr": "192.168.10.0/24",
                    "gateway-ip": "192.168.10.1",
                    "name": "HLM-NET",
                    "network-group": "HLM",
                    "tagged-vlan": false,
                    "vlanid": 101
                },
                {
                    "cidr": "192.168.245.0/24",
                    "gateway-ip": "192.168.245.1",
                    "name": "MANAGEMENT-NET",
                    "network-group": "MANAGEMENT",
                    "tagged-vlan": false,
                    "vlanid": 102
                },

Model supports storing some elements of the list in one file,
and some in another.  This is done by figuring out what the unique "key" field 
is in each dictionary and then tracking which keys appear in which files.  The
disk models are a good example::

        "disk-models": [
            {
                "name": "COMPUTE-DISKS",
                "volume-groups": [
                ] ... details of COMPUTE-DISKS
            {
                "name": "HLM-DISKS",
                "volume-groups": [
                ] ... etc.

            and the corresponding metadata looks like:

            "data/disks_compute.yml": [
                "product",
                {
                    "disk-models": [
                        "COMPUTE-DISKS"
                    ],
                    "keyField": "name",
                    "type": "array"
                },
                "type"
            ],
            "data/disks_hlm.yml": [
                "product",
                {
                    "disk-models": [
                        "HLM-DISKS"
                    ],
                    "keyField": "name",
                    "type": "array"
                },
            ...

    There are only a few dictionaries
       mostly, baremetal, cloud, product, pass-through (perha

       For example, baremetal is in servers.yml, and the metadata looks like:

    "fileInfo": {
        "fileSectionMap": {
            ...
            "data/servers.yml": [
                "product",
                {
                    "keyField": "id",
                    "servers": [
                        "deployer",
                        "ccn-0001",
                        "ccn-0002",
                        "ccn-0003",
                        "COMPUTE-0001",
                        "COMPUTE-0002",
                        "COMPUTE-0003"
                    ],
                    "type": "array"
                },
                "baremetal"    # <- Note that there are no details
            ]
    }},
    "inputModel": {
        "baremetal": {
            "netmask": "255.255.255.0",
            "server-interface": "eth2",
            "subnet": "192.168.10.0"
        }
    }

    "product" is special because it appears in every file

    pass-through is a special object where portions can be split across
    multiple files. Here is what it looks like when only one file has pass-through data:
       
    "fileInfo": {
        "fileSectionMap": {
            "data/pass_through.yml": [
                "product",
                "pass-through"    # NOTE: No detailed info here, just a name
            ],
    }},
    "inputModel": {
        "pass-through": {
            "global": {
                "lib_mysql_java_file_name": "libmysql-java_5.1.32-1_all.deb",
                "thirdparty_folder-env": "/home/stack/stage/thirdparty"
        }}}

       that only go
       
    When pass-through is split among multiple files, each given key in the pass-through dictionary 
    must either:
    1. Be contained entirely in one file, or
    2. Consist of a dictionary, and each of its keys must exist in only a
       single file.

    Here is an example of the second type:

    "fileInfo": {
        "fileSectionMap": {
            "data/cp_pass_through.yml": [
                "product",
                {
                    "pass-through": [   # NOTE: contains an array of keys
                        "global.esx_cloud"  # Note that the key names contain 
                                              dots to represent nested levels,
                                              up to a max of 2
                    ],
                    "type": "object"
                }
            ],
            "data/pass_through.yml": [
                "product",
                {
                    "pass-through": [
                        "global.thirdparty_folder-env",
                        "global.lib_mysql_java_file_name",
                    ],
                    "type": "object"
                }
            ]}},
    "inputModel": {
        "pass-through": {
            "global": {
                "esx_cloud": true,
                "lib_mysql_java_file_name": "libmysql-java_5.1.32-1_all.deb",
                "thirdparty_folder-env": "/home/stack/stage/thirdparty"
            }
        },
    }


Locations
---------
There are few directories that are relevant the to the ardana service:

- ``~/helion/my_cloud/definition/data``

  Contains the data model that is read and manipulated by the REST operations
  that begin with ``/model``

- templates

- xxx
  git-controlled dir

- xxx
  output of config processor

