#!/usr/bin/env python

'''Python Cookbook.

Copyright 2015 Li Yun.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import sys
import unittest

try:
    import pep8
except ImportError:
    sys.exit('pep8 required: `pip install pep8`')


class GeneralTestCase(unittest.TestCase):

    def setUp(self):
        self.test_modules = [__file__]
        self.pep8_quiet = False

    def test_py_version_conformance(self):
        # Python 2.7.9+ or 3.4+ required
        if sys.version_info.major == 2:
            self.assertEqual(sys.version_info.minor, 7,
                             'Python 2.7.9+ required')
            self.assertGreaterEqual(sys.version_info.micro, 9,
                                    'Python 2.7.9+ required')
        elif sys.version_info.major == 3:
            self.assertGreaterEqual(sys.version_info.minor, 4,
                                    'Python 3.4+ required')

    def test_pep8_conformance(self):
        pep8_style = pep8.StyleGuide(quiet=self.pep8_quiet)
        result = pep8_style.check_files(self.test_modules)
        self.assertEqual(result.total_errors, 0,
                         'Found {0} code style errors (and warnings)'
                         .format(result.total_errors))


if __name__ == '__main__':
    unittest.main(verbosity=2, catchbreak=True)
