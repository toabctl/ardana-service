import copy
import os
import pdb
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

        affected_files = [k for k,v in changes.iteritems()
                          if v['status'] != model.IGNORED]
        self.assertEquals(0, len(affected_files))


    def test_add_servers(self):
        data = model.read_model(self.model_dir)

        before_len = len(data['inputModel']['servers'])

        num_to_add = 5
        # grab last server and make extra copies of it
        server = data['inputModel']['servers'][-1:][0]
        for i in range(0, num_to_add):
            clone = copy.deepcopy(server)
            clone['id'] = 'server-%s' % i
            data['inputModel']['servers'].append(clone)

        changes = model.write_model(data, self.model_dir, dry_run=True)
        changed_files = [k for k,v in changes.iteritems()
                         if v['status'] == model.CHANGED]

        self.assertEquals(1, len(changed_files))
        self.assertEquals(changed_files[0], "data/servers.yml")
        after_len = len(changes[changed_files[0]]['data']['servers'])
        self.assertEquals(before_len+num_to_add, after_len)


    def test_add_disk_models(self):
        data = model.read_model(self.model_dir)

        before_len = len(data['inputModel']['servers'])

        num_to_add = 5
        # grab last disk model and make extra copies of it
        disk_model = data['inputModel']['disk-models'][-1:][0]
        for i in range(0, num_to_add):
            clone = copy.deepcopy(disk_model)
            clone['name'] = 'model-%s' % i
            data['inputModel']['disk-models'].append(clone)

        changes = model.write_model(data, self.model_dir, dry_run=True)
        print "test_add_disk_models: ", {k:v['status'] for k,v in changes.iteritems() if v['status'] != 'ignored'}
        added_files = [k for k,v in changes.iteritems()
                       if v['status'] == model.ADDED]

        self.assertEquals(num_to_add, len(added_files))


    @unittest.skip("Skipping")
    def test_add_split_models(self):
        pass


    @unittest.skip("Skipping")
    def test_add_new_section(self):
        pass


    @unittest.skip("Skipping")
    def test_update_pass_through(self):
        # Note: need to add pass-through to the existing test data
        pass


    @unittest.skip("Skipping")
    def test_add_pass_through(self):
        pass


    @unittest.skip("Skipping")
    def test_delete_pass_through(self):
        pass


    @unittest.skip("Skipping")
    def test_add_new_object(self):
        pass


    @unittest.skip("Skipping")
    def test_write_two_non_split_objects(self):
        pass

