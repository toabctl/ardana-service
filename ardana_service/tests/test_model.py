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
