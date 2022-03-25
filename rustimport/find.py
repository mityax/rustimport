import os
import sys
from typing import Optional, Iterable

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
            #print(f"Trying: {os.path.join(pth, modulepath)}")
            if i := importable.try_create(os.path.join(pth, modulepath), fullname=modulename, opt_in=opt_in):
                return i

    #return _find_importable_in_folders(abs_matching_dirs, modulename, opt_in)


def _find_matching_path_dirs(moduledir):
    if moduledir == "":
        return sys.path

    ds = []
    for folder in sys.path:
        test_path = os.path.join(folder, moduledir)
        if os.path.isdir(test_path):
            ds.append(test_path)
    return ds


def _find_importable_in_folders(folders: Iterable[str], modulename: str, opt_in: bool) -> Optional[Importable]:
    for folder in folders:
        for importable in all_importables:
            if i := importable.try_create(os.path.join(folder, modulename), opt_in):
                return i
    return None
