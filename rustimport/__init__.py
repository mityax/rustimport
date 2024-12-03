# See CONTRIBUTING.md for a description of the project structure and the internal logic.

"""
rustimport - Import Rust source files directly from Python!

Example:
Save the Rust code below as somecode.rs.

```rust
// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn square(x: i32) -> i32 {
    x * x
}
```

Then open a Python interpreter and import the Rust extension:

```python
>>> import rustimport.import_hook
>>> import somecode  # This will pause for a moment to compile the module
>>> somecode.square(9)
81
```

Hurray, you've called some Rust code from Python using a combination of rustimport and pyo3!

For more information check the Readme on GitHub: https://github.com/mityax/rustimport
"""

import logging as _logging
from shutil import which
from types import ModuleType

from rustimport import settings
from rustimport.error_handling import BuildError

_logger = _logging.getLogger("rustimport")


def imp(fullname, opt_in: bool = False, force_rebuild: bool = settings.force_rebuild) -> ModuleType:
    """
    Explicit alternative to using rustimport.import_hook.

    @param fullname: The name of the module to import.
    @param opt_in: Whether to require rust sources to opt in via adding "rustimport" to the first line of the file/crate.
                   Default is False since the intent to import a Rust module is explicitly stated.
    @param force_rebuild: Whether to force re-compilation of the extension, even if it hasn't changed. Default is
                          derived from settings.

    @return: The compiled and loaded Python extension module.
    """
    from rustimport.load import dlopen_flags

    if settings.release_mode:
        import importlib
        with dlopen_flags():
            return importlib.import_module(fullname)

    from rustimport.find import find_module_importable
    from rustimport.importable import should_rebuild

    importable = find_module_importable(fullname, opt_in)

    if should_rebuild(importable, force_rebuild=force_rebuild):
        importable.build(release=settings.compile_release_binaries)

    return importable.load()


def imp_from_path(path, fullname=None, opt_in: bool = False, force_rebuild: bool = settings.force_rebuild) -> ModuleType:
    """
    Imports a Rust module from a specified file path.

    @param path: The path to the Rust file or crate.
    @param fullname: The name of the module to import. Defaults to inferring from the file/crate path if not specified.
    @param opt_in: Whether to require rust sources to opt in via adding "rustimport" to the first line of the file/crate.
                   Default is False since the intent to import a Rust module is explicitly stated.
    @param force_rebuild: Whether to force re-compilation of the extension, even if it hasn't changed. Default is
                          derived from settings.

    @return: The compiled and loaded Python extension module.
    """
    from rustimport.load import dlopen_flags

    if settings.release_mode:
        import importlib
        with dlopen_flags():
            return importlib.import_module(fullname)

    from rustimport.importable import all_importables
    from rustimport.importable import should_rebuild

    for importable in all_importables:
        if i := importable.try_create(path, fullname=fullname, opt_in=opt_in):
            if should_rebuild(i, force_rebuild=force_rebuild):
                i.build(release=settings.compile_release_binaries)
            return i.load()


def build(fullname, opt_in: bool = False, force_rebuild: bool = settings.force_rebuild,
          release: bool = settings.compile_release_binaries):
    """
    Builds a rust extension without importing it.

    @param fullname: The name of the rust file/crate to build.
    @param opt_in: Whether to require rust sources to opt in via adding "rustimport" to the first line of the file/crate.
                   Default is False since the intent to import a Rust module is explicitly stated.
    @param force_rebuild: Whether to force re-compilation of the extension, even if it hasn't changed. Default is
                          derived from settings.
    @param release: Whether to build a release binary. Default is derived from settings.

    @return: An [Importable] instance for the given extension.
    """
    from rustimport.find import find_module_importable
    from rustimport.importable import should_rebuild

    importable = find_module_importable(fullname, opt_in=opt_in)
    if should_rebuild(importable, force_rebuild=force_rebuild, force_release=release):
        importable.build(release=release)

    return importable


def build_filepath(path, opt_in: bool = False, force_rebuild: bool = settings.force_rebuild,
                   release: bool = settings.compile_release_binaries):
    """
    Builds a rust extension module from a specified file path, without importing it.

    @param path: The file path to the rust file or crate.
    @param opt_in: Whether to require rust sources to opt in via adding "rustimport" to the first line of the file/crate.
                   Default is False since the intent to import a Rust module is explicitly stated.
    @param force_rebuild: Whether to force re-compilation of the extension, even if it hasn't changed. Default is
                          derived from settings.
    @param release: Whether to build a release binary. Default is derived from settings.

    @return: An [Importable] instance for the given extension.
    """

    from rustimport.importable import all_importables
    from rustimport.importable import should_rebuild

    for importable in all_importables:
        if i := importable.try_create(path, opt_in=opt_in):
            if should_rebuild(i, force_rebuild=force_rebuild, force_release=release):
                i.build(release=release)
                return importable


def build_all(root_directory, opt_in: bool = True, force_rebuild: bool = settings.force_rebuild,
              release: bool = settings.compile_release_binaries):
    """
    Builds all eligible rust extensions modules in the specified directory.

    @param root_directory: The root directory to recursively search for rust source files/crates.
    @param opt_in: Whether to require rust sources to opt in via adding "rustimport" to the first line of the file/crate.
                   Default is True.
    @param force_rebuild: Whether to force re-compilation of the extension, even if it hasn't changed. Default is
                          derived from settings.
    @param release: Whether to build a release binary. Default is derived from settings.

    @return: A tuple of two lists of [Importable]s, one with the built [Importable]s and one with those
             skipped: `(built, not_built)`
    """
    import os
    from rustimport.importable import (
        SingleFileImportable,
        CrateImportable,
        should_rebuild,
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
        if should_rebuild(i, force_rebuild=force_rebuild, force_release=release):
            _logger.info(f"Building {i.path} ({index + 1}/{len(importables)})…")
            i.build(release=release)
        else:
            not_built.append(i)

    if not_built:
        _logger.info(f"Skipped building {len(not_built)} {'extension' if len(not_built) == 1 else 'extensions'} due"
                     f" to unchanged source files. Re-run with `--force` to rebuild everything.")

    _logger.info("Completed successfully.")

    return [i for i in importables if i not in not_built], not_built


def load_ipython_extension(ipython):
    """IPython magic entry point."""
    rustc_is_installed = which("rustc") is not None
    if not rustc_is_installed:
        msg = "rustc must be installed to ust rustimport"
        raise OSError(msg)

    # Delay import RustImportIPython so that IPython is a soft dependency
    from rustimport.ipython_magic import RustImportIPython

    ipython.register_magics(RustImportIPython)


__all__ = [
    'settings', 'imp', 'imp_from_path', 'build',
    'build_filepath', 'build_all', 'BuildError',
]
