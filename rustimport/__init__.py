"""
See CONTRIBUTING.md for a description of the project structure and the internal logic.
"""
import logging as _logging
from types import ModuleType

from rustimport import settings

_logger = _logging.getLogger("rustimport")


def imp(fullname, opt_in: bool=False, force_rebuild: bool=settings.force_rebuild) -> ModuleType:
    """
    `imp` is the explicit alternative to using rustimport.import_hook.

    Parameters
    ----------
    fullname : the name of the module to import.
    opt_in : should we require rust files to opt in via adding "rustimport" to
             the first line of the file? This is on by default for the
             import hook, but is off by default for this function since the
             intent to import a rust module is clearly specified.

    Returns
    -------
    module : the compiled and loaded Python extension module
    """
    if settings.release_mode:
        import importlib
        return importlib.import_module(fullname)

    from rustimport.find import find_module_importable

    importable = find_module_importable(fullname, opt_in)
    if force_rebuild or (not settings.release_mode and importable.needs_rebuild()):
        importable.build()
    return importable.load()


def imp_from_path(path, fullname=None, opt_in: bool=False, force_rebuild: bool=settings.force_rebuild) -> ModuleType:
    """
    `imp_from_path` serves the same purpose as `imp` except allows
    specifying the exact path of the rust file or crate.

    Parameters
    ----------
    filepath : the filepath to the C++ file to build and import.
    fullname : the name of the module to import. This can be different from the
               module name inferred from the filepath if desired.

    Returns
    -------
    module : the compiled and loaded Python extension module
    """
    if settings.release_mode:
        import importlib
        return importlib.import_module(fullname)

    from rustimport.importable import all_importables

    for importable in all_importables:
        if i := importable.try_create(path, fullname=fullname, opt_in=opt_in):
            if force_rebuild or (not settings.release_mode and i.needs_rebuild()):
                i.build()
            return importable.load()


def build(fullname, opt_in: bool=False, force_rebuild: bool=settings.force_rebuild, release: bool=False):
    """
    `build` builds a extension module like `imp` but does not import the
    extension.

    Parameters
    ----------
    fullname : the name of the module to import.

    Returns
    -------
    ext_path : the path to the compiled extension.
    """
    from rustimport.find import find_module_importable

    importable = find_module_importable(fullname, opt_in=opt_in)
    if force_rebuild or importable.needs_rebuild(release=release):
        importable.build(release=release)
    return importable


def build_filepath(path, opt_in: bool=False, force_rebuild: bool=settings.force_rebuild, release: bool=False):
    """
    `build_filepath` builds a extension module like `build` but allows
    to directly specify a file path.

    Parameters
    ----------
    filepath : the filepath to the C++ file to build.
    fullname : the name of the module to build.

    Returns
    -------
    ext_path : the path to the compiled extension.
    """

    from rustimport.importable import all_importables

    for importable in all_importables:
        if i := importable.try_create(path, opt_in=opt_in):
            if force_rebuild or importable.needs_rebuild(release=release):
                importable.build(release=release)
                return importable


def build_all(root_directory, opt_in: bool=True, force_rebuild: bool=settings.force_rebuild, release: bool=False):
    """
    `build_all` builds a extension module like `build` for each eligible (that is,
    containing the "rustimport" header) source file within the given `root_directory`.

    Parameters
    ----------
    root_directory : the root directory to search for cpp source files in.
    """
    import os
    from rustimport.importable import (
        SingleFileImportable,
        CrateImportable,
    )

    importables = []

    _logger.info(f"Collecting rust extensions in {root_directory}…")
    for directory, subdirs, files in os.walk(root_directory, topdown=True):
        if any(f.lower() == 'cargo.toml' for f in files):
            if i := CrateImportable.try_create(directory, opt_in=opt_in):
                importables.append(i)
            # We never recurse into subdirectories of crates:
            del subdirs[:]
        else:
            for file in files:
                if os.path.splitext(file)[1] == '.rs':
                    i = SingleFileImportable.try_create(os.path.join(directory, file), opt_in=opt_in)
                    if i is not None:
                        importables.append(i)

    _logger.info(f"Found {len(importables)} {'extension' if len(importables) == 1 else 'extensions'}.")
    not_built = []
    for index, i in enumerate(importables):
        if force_rebuild or i.needs_rebuild(release=release):
            _logger.info(f"Building {i.path} ({index + 1}/{len(importables)})…")
            i.build(release=release)
        else:
            not_built.append(i)

    if not_built:
        _logger.info(f"Skipped building {len(not_built)} {'extension' if len(not_built) == 1 else 'extensions'} due"
                     f" to unchanged source files. Re-run with `--force-rebuild` to rebuild everything.")
    _logger.info("Completed successfully.")


class BuildError(Exception):
    """Raised if building a native rust extension fails"""


__all__ = [
    'settings', 'imp', 'imp_from_path', 'build',
    'build_filepath', 'build_all', 'BuildError',
]
