import unittest
from unittest.mock import patch
from textwrap import dedent

from IPython.testing.globalipapp import get_ipython
from rustimport.error_handling import BuildError
from rustimport import load_ipython_extension


class TestIPythonMagic(unittest.TestCase):
    @classmethod
    def setUp(cls) -> None:
        if not hasattr(cls, "ip"):
            cls.ip = get_ipython()
            cls.ip.run_cell(r"%load_ext rustimport")

        cls.square_cell = dedent(
            """use pyo3::prelude::*;

            #[pyfunction]
            fn square(x: i32) -> i32 {
                x * x
            }
            """
        )

    def test_helloworld_error(self):
        with self.assertRaises(BuildError):
            self.ip.run_cell_magic("rustimport", "", "hello world")

    def test_square(self):
        self.ip.run_cell_magic("rustimport", "", self.square_cell)

        self.assertIn("square", self.ip.user_ns)
        self.assertEqual(self.ip.user_ns["square"](12), 144)

    def test_square_twice(self):
        self.ip.run_cell_magic("rustimport", "", self.square_cell)
        self.ip.run_cell_magic("rustimport", "", self.square_cell)

        self.assertIn("square", self.ip.user_ns)
        self.assertEqual(self.ip.user_ns["square"](12), 144)

    def test_square_release(self):
        self.ip.run_cell_magic("rustimport", "-r -f", self.square_cell)

        self.assertIn("square", self.ip.user_ns)
        self.assertEqual(self.ip.user_ns["square"](9), 81)

    def test_module_path_variable(self):
        self.ip.run_cell_magic(
            "rustimport", "--module-path-variable=my_module", self.square_cell
        )

        self.assertIn("my_module", self.ip.user_ns)


class TestLoadIPythonExtension(unittest.TestCase):
    @patch("rustimport.which")
    def test_import_error(self, which_mock):
        which_mock.return_value = None

        with self.assertRaises(OSError):
            load_ipython_extension(None)


if __name__ == "__main__":
    unittest.main()
