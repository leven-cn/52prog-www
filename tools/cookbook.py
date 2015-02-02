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


def py_version_validate():
    if sys.version_info.major == 2:
        if sys.version_info.minor != 7 or sys.version_info.micro < 9:
            sys.exit('Python 2.7.9+ required')
    elif sys.version_info.major == 3:
        if sys.version_info.minor < 4:
            sys.exit('Python 3.4+ required')
    else:
        sys.exit('Python 2.7.9+ or 3.4+ required')


class CodeStyleTestCase(unittest.TestCase):

    def test_pep8_conformance(self):
        pep8_style = pep8.StyleGuide(quiet=False)
        result = pep8_style.check_files([__file__])
        self.assertEqual(result.total_errors, 0,
                         'Found {0} code style errors (and warnings)'
                         .format(result.total_errors))


if __name__ == '__main__':
    py_version_validate()
    unittest.main(verbosity=2, catchbreak=True)
