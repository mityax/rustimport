import os
import sys

from rustimport.error_handling import get_potential_failure_reasons
from rustimport.importable import all_importables, Importable


def find_module_importable(modulename: str, opt_in: bool = False) -> Importable:
    importable = _find_importable(modulename, opt_in)
    if importable is None:
        reasons_list = "\n".join([
            "  - " + "\n    ".join(r.splitlines())
            for r in get_potential_failure_reasons()
        ])
        raise ImportError(
            f"Couldn't find a valid import target matching the module name: {modulename} (opt_in: {opt_in})." +
            (f" This could be potential reasons: \n{reasons_list}" if reasons_list else "")
        )
    return importable


def _find_importable(modulename, opt_in=False):
    modulepath = modulename.replace(".", os.sep)

    for pth in sys.path:
        for importable in all_importables:
            if i := importable.try_create(os.path.join(pth, modulepath), fullname=modulename, opt_in=opt_in):
                return i

