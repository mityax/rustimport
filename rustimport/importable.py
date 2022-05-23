import abc
import hashlib
import logging
import os.path
import shutil
import sysconfig
import types
from typing import Optional, List, Type

from rustimport import load, BuildError, settings
from rustimport.checksum import is_checksum_valid, save_checksum
from rustimport.compiler import Cargo
from rustimport.pre_processing import Preprocessor

_logger = logging.getLogger(__name__)


class Importable(abc.ABC):
    """Abstract interface for importable rust entities"""

    def __init__(self, path: str, fullname: Optional[str] = None):
        self.path = os.path.realpath(path)
        self.fullname = fullname or os.path.splitext(os.path.basename(path))[0]

    @property
    def extension_path(self):
        return os.path.join(os.path.dirname(self.path), self.name) + get_extension_suffix()

    @property
    def build_tempdir(self):
        return os.path.join(settings.cache_dir, f'{self.fullname}-{hashlib.md5(self.path.encode()).hexdigest()}')

    @property
    def name(self):
        return self.fullname.split('.')[-1]

    @property
    def dependencies(self):
        return [self.path]

    @classmethod
    @abc.abstractmethod
    def try_create(cls, path: str, fullname: Optional[str] = None, opt_in: bool = True) -> Optional['Importable']:
        """
        Try to create an importable for the given file system path or return `None` if
        this is not possible.

        @param opt_in: If true, indicates the user's preference to require manual opt-in. This may
                       be ignored by some implementations, if it is not applicable.
        @return: Either an `Importable` instance or `None`
        """
        raise NotImplemented

    def needs_rebuild(self, release: bool = False) -> bool:
        if not os.path.isfile(self.extension_path):
            return True
        if not is_checksum_valid(self.extension_path, self.dependencies, release=release):
            return True
        return False

    @abc.abstractmethod
    def build(self, release: bool = False):
        """
        Build the native extension for this `Importable`.

        @raises: `BuildError` if compilation fails.
        """
        raise NotImplemented

    def load(self) -> types.ModuleType:
        """Load the native extension for this `Importable`, if it exists."""
        return load.load_module(self.extension_path, self.fullname)


class SingleFileImportable(Importable):
    """Importable for single-file rust libraries (a single .rs file)"""

    @property
    def dependencies(self):
        directory = os.path.dirname(self.path)
        p = Preprocessor(self.path, lib_name=self.name).process()
        return [
            self.path,
            *[os.path.join(directory, d) for d in p.dependency_file_patterns]
        ]

    @property
    def __crate_name(self):
        return os.path.splitext(os.path.basename(self.path))[0]

    @classmethod
    def try_create(cls, path: str, fullname: Optional[str] = None, opt_in: bool = True) -> Optional['SingleFileImportable']:
        if not path.endswith('.rs'):
            path += '.rs'

        if os.path.isfile(path):
            if opt_in and not _check_first_line_contains_rustimport(path):
                return None

            _logger.debug(f"[try_import]: Successfully created SingleFileImportable to import from {path}.")
            return SingleFileImportable(path, fullname=fullname)
        _logger.debug(f"[try_import]: Failed to create a SingleFileImportable to import from {path}.")

    def build(self, release: bool = False):
        path = os.path.join(self.build_tempdir, self.__crate_name)

        _logger.debug(f"Building in temporary directory {path}")
        src_path = os.path.join(path, 'src')

        os.makedirs(src_path, exist_ok=True)

        preprocessed = Preprocessor(self.path, lib_name=self.name).process()

        if preprocessed.updated_source is not None:
            with open(os.path.join(src_path, 'lib.rs'), 'wb+') as f:
                f.write(preprocessed.updated_source)
        else:
            shutil.copy2(self.path, os.path.join(src_path, 'lib.rs'))

        with open(os.path.join(path, 'Cargo.toml'), 'wb+') as f:
            f.write(preprocessed.cargo_manifest)

        build_result = Cargo().build(
            path,
            destination_path=self.extension_path,
            release=release,
            additional_args=preprocessed.additional_cargo_args,
        )

        if not build_result.success:
            raise BuildError(f"Failed to build {self.path}")

        save_checksum(self.extension_path, self.dependencies, release=release)


class CrateImportable(Importable):
    """Importable allowing to import a whole rust crate directory."""

    @property
    def __crate_path(self):
        return os.path.dirname(self.__manifest_path)

    @property
    def __manifest_path(self):
        return self.path if self.path.lower().endswith("/cargo.toml") else os.path.join(self.path, 'Cargo.toml')

    @property
    def dependencies(self):
        src_path = os.path.join(self.__crate_path, 'src')
        p = Preprocessor(os.path.join(src_path, 'lib.rs'), lib_name=self.name).process()
        return [
            os.path.join(self.__crate_path, '**/*.rs'),
            os.path.join(self.__crate_path, '**/Cargo.*'),
            *[os.path.join(src_path, d) for d in p.dependency_file_patterns],
        ]

    @classmethod
    def try_create(cls, path: str, fullname: Optional[str] = None, opt_in: bool = True) -> Optional['Importable']:
        manifest_path = path if path.lower().endswith("/cargo.toml") else os.path.join(path, 'Cargo.toml')
        directory = os.path.dirname(manifest_path)

        if os.path.isfile(manifest_path):
            if opt_in \
                    and not os.path.isfile(os.path.join(directory, '.rustimport')) \
                    and not _check_first_line_contains_rustimport(manifest_path):
                return None
            return CrateImportable(path=directory, fullname=fullname)

    def build(self, release: bool = False):
        output_path = os.path.join(self.build_tempdir, os.path.basename(self.__crate_path))
        _logger.debug(f"Building in temporary directory {output_path}")

        os.makedirs(output_path, exist_ok=True)
        shutil.copytree(self.__crate_path, output_path, dirs_exist_ok=True)

        preprocessed = Preprocessor(
            os.path.join(self.__crate_path, 'src/lib.rs'),
            lib_name=self.name,
            cargo_manifest_path=os.path.join(self.__crate_path, 'Cargo.toml'),
        ).process()

        if preprocessed.updated_source is not None:
            with open(os.path.join(output_path, 'src/lib.rs'), 'wb') as f:
                f.write(preprocessed.updated_source)

        with open(os.path.join(output_path, 'Cargo.toml'), 'wb') as f:
            f.write(preprocessed.cargo_manifest)

        build_result = Cargo().build(
            output_path,
            destination_path=self.extension_path,
            release=release,
            additional_args=preprocessed.additional_cargo_args,
        )

        if not build_result.success:
            raise BuildError(f"Failed to build {self.path}")

        save_checksum(self.extension_path, self.dependencies, release=release)


all_importables: List[Type[Importable]] = [
    SingleFileImportable,
    CrateImportable
]


def _check_first_line_contains_rustimport(filepath: str) -> bool:
    with open(filepath, "r") as f:
        while not (line := f.readline().strip()):  # skip empty lines
            pass
        return "rustimport" in line


def get_extension_suffix():
    sysvar = sysconfig.get_config_var  # just an abbreviation for below
    return sysvar("EXT_SUFFIX") or sysvar("SO") or '.so'


def should_rebuild(imp: Importable, force_rebuild: bool = False, force_release: bool = False):
    """
    Utility to check whether the given `Importable` should be re-built, based on the given
    `force_rebuild` and `force_release` preferences as well as the global settings.
    """

    if settings.release_mode:
        return False
    if settings.force_rebuild or force_rebuild:
        return True
    return imp.needs_rebuild(release=settings.compile_release_binaries or force_release)
