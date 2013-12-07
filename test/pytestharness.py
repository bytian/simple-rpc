#!/usr/bin/env python

import unittest
from unittest import TestCase
import sys
import os
sys.path += os.path.abspath(os.path.join(os.path.split(__file__)[0], "../pylib")),
import simplerpc

class TestUtils(TestCase):
    def test_cpp_python_interop(self):
        assert simplerpc.a_add_b(1, 2) == 3

if __name__ == "__main__":
    unittest.main()
