import os
import sys

from rustimport.importable import all_importables, Importable


def find_module_importable(modulename: str, opt_in: bool = False) -> Importable:
    importable = _find_importable(modulename, opt_in)
    if importable is None:
        raise ImportError(
            f"Couldn't find a file or crate matching the module"
            f" name: {modulename} (opt_in: {opt_in})"
        )
    return importable


def _find_importable(modulename, opt_in=False):
    modulepath = modulename.replace(".", os.sep)

    for pth in sys.path:
        for importable in all_importables:
            if i := importable.try_create(os.path.join(pth, modulepath), fullname=modulename, opt_in=opt_in):
                return i

