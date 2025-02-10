import os.path
import shutil
import sys
import tempfile
import unittest

from rustimport import import_hook  # noqa


class TestExamples(unittest.TestCase):
    """
    This test case just tests importing each of the examples and running a simple function from them.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.examples_modules_tempdir = tempfile.TemporaryDirectory(suffix='-rustimport-tests-examples')
        shutil.copytree(
            os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'examples'),
            os.path.join(cls.examples_modules_tempdir.name, "rustimport_examples"),
            ignore=shutil.ignore_patterns("*.so", "*.dll", "target"),
        )
        sys.path.append(cls.examples_modules_tempdir.name)  # noqa

    @classmethod
    def tearDownClass(cls) -> None:
        sys.path.remove(cls.examples_modules_tempdir.name)  # noqa
        cls.examples_modules_tempdir.cleanup()  # noqa

    def test_string_sum(self):
        from rustimport_examples import string_sum  # noqa

        self.assertEqual(string_sum.sum_as_string(1, 2), "3")

    def test_crate(self):
        from rustimport_examples import test_crate  # noqa

        self.assertEqual(test_crate.say_hello(), "Hello from test_crate, implemented in Rust!")

    def test_workspace(self):
        from rustimport_examples.test_workspace import crate_a  # noqa
        from rustimport_examples.test_workspace import crate_c  # noqa

        self.assertEqual(crate_a.double(2), 4)
        self.assertEqual(crate_c.fibanocci(10), [1, 1, 2, 3, 5, 8, 13, 21, 34, 55])

    def test_cpython_doublecount(self):
        from rustimport_examples import cpython_doublecount as s  # noqa

        self.assertEqual(s.count_doubles("May the good lord make this assertion succeed. Amen!"), 4)

    def test_pyo3_minimal(self):
        from rustimport_examples import pyo3_minimal  # noqa

        self.assertEqual(pyo3_minimal.say_hello(), "Hello from Rust!")

    def test_pyo3_no_template(self):
        from rustimport_examples import pyo3_no_template as s  # noqa

        self.assertEqual(s.sum_as_string(3, 4), "7")

    def test_pyo3_manifest_only_templating(self):
        from rustimport_examples import pyo3_manifest_only_templating as s  # noqa

        self.assertEqual(s.try_divide(10, 2), 5)

        with self.assertRaises(ValueError):
            s.try_divide(2, 0)

    def test_pyo3_basic(self):
        from rustimport_examples import pyo3_basic as s  # noqa

        res = s.random_number_from_rust(5, 200)

        self.assertGreaterEqual(res, 5)
        self.assertLess(res, 200)  # rust's `Rng::gen_range(a...b)` excludes the upper limit, but includes the lower

    def test_relative_path_dependency(self):
        from rustimport_examples import relative_path_dependency as s  # noqa

        self.assertIsInstance(s.say_hello(), str)

    def test_crate_relative_path_dependency(self):
        from rustimport_examples import crate_relative_path_dependency as s  # noqa

        self.assertIsInstance(s.say_hello(), str)

    def test_pyo3_structs_and_enums(self):
        from rustimport_examples import pyo3_structs_and_enums as s  # noqa

        with self.assertRaisesRegex(TypeError, "No constructor defined for MyStruct"):
            s.MyStruct(5)

        my_other_struct = s.MyOtherStruct(5)
        self.assertEqual(my_other_struct.get_doubled_value(), 10)

        self.assertEqual(s.MyEnum.A, s.MyEnum.A)
        self.assertNotEqual(s.MyEnum.A, s.MyEnum.B)

        self.assertEqual(s.MyOtherEnum.B(value=42), s.MyOtherEnum.B(value=42))
        self.assertNotEqual(s.MyOtherEnum.C("some message"), s.MyOtherEnum.A)

    def test_pyo3_declarative_module(self):
        from rustimport_examples import pyo3_declarative_module as s  # noqa

        self.assertEqual(s.say_hello(), "Hello from declarative_module!")



if __name__ == '__main__':
    unittest.main()
