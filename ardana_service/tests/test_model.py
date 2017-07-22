import copy
import os
import unittest
import yaml

from .. import model

class MyTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MyTest, self).__init__(*args, **kwargs)
        self.model_dir = os.path.join(os.path.dirname(__file__), 'test_data')

    def test_read_valid_model(self):
        data = model.read_model(self.model_dir)
        self.assertIsNotNone(data)

    def test_read_model_missing_config(self):
        model_dir = os.path.join(os.path.dirname(__file__), 'test_data_invalid', 'no_config')
        with self.assertRaises(IOError):
            model.read_model(model_dir)

    def test_read_invalid_yml(self):
        model_dir = os.path.join(os.path.dirname(__file__), 'test_data_invalid', 'invalid_yml')
        with self.assertRaises(yaml.YAMLError):
            model.read_model(model_dir)

    def test_read_invalid_dir(self):
        model_dir = os.path.join(os.path.dirname(__file__), 'test_data_invalid', 'doesnotexist')
        with self.assertRaises(IOError):
            model.read_model(model_dir)


    def test_no_changes(self):

        data = model.read_model(self.model_dir)
        changes = model.write_model(data, self.model_dir, dry_run=True)

        changed_files = [k for k,v in changes.iteritems()
                        if v.get('changed', False)]
        self.assertEquals(0, len(changed_files), "No files should have changed")

    def test_add_servers(self):

        num_to_add = 5

        data = model.read_model(self.model_dir)

        before_len = len(data['inputModel']['servers'])
        server = data['inputModel']['servers'][-1:][0]
        for i in range(0, num_to_add):
            clone = copy.deepcopy(server)
            clone['id'] = 'server-%s' % i
            data['inputModel']['servers'].append(clone)

        changes = model.write_model(data, self.model_dir, dry_run=True)
        changed_files = [k for k,v in changes.iteritems()
                        if v.get('changed', False)]

        self.assertEquals(1, len(changed_files), "Only should have written one file")
        self.assertEquals(changed_files[0], "data/servers.yml",
            "Only should have written servers file")
        after_len = len(changes[changed_files[0]]['data']['servers'])
        self.assertEquals(before_len+num_to_add, after_len, "Should have written %s more" % num_to_add)
