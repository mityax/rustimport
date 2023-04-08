import os.path
import shutil
import sys
import tempfile
import unittest

from rustimport import import_hook  # noqa


class TestExamples(unittest.TestCase):
    """
    This test case just tests importing each of the examples and running
    a simple function from them.
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

    def test_doublecount(self):
        from rustimport_examples import doublecount  # noqa

        self.assertEqual(doublecount.count_doubles("May the good lord make this assertion succeed. Amen!"), 4)

    def test_minimal(self):
        from rustimport_examples import minimal  # noqa

        self.assertEqual(minimal.say_hello(), "Hello from Rust!")

    def test_singlefile(self):
        from rustimport_examples import singlefile  # noqa

        self.assertEqual(singlefile.sum_as_string(3, 4), "7")

    def test_singlefile_manifest_only_templating(self):
        from rustimport_examples import singlefile_manifest_only_templating as s  # noqa

        self.assertEqual(s.try_divide(10, 2), 5)

        with self.assertRaises(ValueError):
            s.try_divide(2, 0)

    def test_singlefile_templating(self):
        from rustimport_examples import singlefile_templating as s  # noqa

        res = s.random_number_from_rust(5, 200)

        self.assertGreaterEqual(res, 5)
        self.assertLess(res, 200)  # rust's `Rng::gen_range(a...b)` excludes the upper limit, but includes the lower


if __name__ == '__main__':
    unittest.main()
