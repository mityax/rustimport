import unittest  # noqa


# Before doing anything, check that rustimport is importable:
try:
    import rustimport
except:
    raise ImportError("Cannot import rustimport. Make sure to have it in your path or, preferably, "
                      "install it in your venv in editable mode using: `pip install -e .`")

from test_examples import *  # noqa
from test_cli import *  # noqa


if __name__ == "__main__":
    unittest.main()
