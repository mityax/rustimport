import abc
import hashlib
import logging
import os.path
import shutil
import sysconfig
import tempfile
import types
from functools import cached_property
from typing import Optional

from rustimport import importer, BuildError, settings
from rustimport.checksum import is_checksum_valid, checksum_save
from rustimport.compiler import Cargo

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
    def try_create(cls, path: str, fullname: Optional[str], opt_in: bool = True) -> Optional['Importable']:
        """
        Try to create an importable for the given file system path or return `None` if
        this is not possible.

        @param opt_in: If true, indicates the user's preference to require manual opt-in. This may
                       be ignored by some implementations, if it is not applicable.
        @return: Either an `Importable` instance or `None`
        """
        raise NotImplemented

    @property
    def needs_rebuild(self) -> bool:
        if not os.path.isfile(self.extension_path):
            return True
        if not is_checksum_valid(self.extension_path, self.dependencies):
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
        return importer.load_module(self.extension_path, self.fullname)


class SingleFileImportable(Importable):
    """Importable for single-file rust libraries (a single .rs file)"""

    @property
    def __crate_name(self):
        return os.path.splitext(os.path.basename(self.path))[0]

    @classmethod
    def try_create(cls, path: str, fullname: Optional[str], opt_in: bool = True) -> Optional['SingleFileImportable']:
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
        shutil.copy2(self.path, os.path.join(src_path, 'lib.rs'))

        with open(os.path.join(path, 'Cargo.toml'), 'wb+') as f:
            f.write(self.__cargo_manifest)

        build_result = Cargo().build(
            path,
            destination_path=self.extension_path,
            release=release,
        )

        if not build_result.success:
            raise BuildError(f"Failed to build {self.path}")

        checksum_save(self.extension_path, self.dependencies)

    @cached_property
    def __cargo_manifest(self) -> bytes:
        manifest = b''
        with open(self.path, 'rb') as f:
            for line in (l.strip() for l in f):
                if line and not line.startswith(b"//"):
                    break
                if line.startswith(b'//:'):
                    manifest += line[3:].lstrip() + b'\n'
        return manifest + b'\n'


class CrateImportable(Importable):

    @property
    def __crate_path(self):
        return os.path.dirname(self.__manifest_path)

    @property
    def __manifest_path(self):
        return self.path if self.path.lower().endswith("/cargo.toml") else os.path.join(self.path, 'Cargo.toml')

    @property
    def dependencies(self):
        return [
            os.path.join(self.__crate_path, '**/*.rs'),
            os.path.join(self.__crate_path, '**/Cargo.*'),
        ]

    @classmethod
    def try_create(cls, path: str, fullname: Optional[str], opt_in: bool = True) -> Optional['Importable']:
        manifest_path = path if path.lower().endswith("/cargo.toml") else os.path.join(path, 'Cargo.toml')
        directory = os.path.dirname(manifest_path)

        if os.path.isfile(manifest_path):
            if opt_in \
                    and not os.path.isfile(os.path.join(directory, '.rustimport')) \
                    and not _check_first_line_contains_rustimport(manifest_path):
                return None

            return CrateImportable(path=directory, fullname=fullname)

    def build(self, release: bool = False):
        path = os.path.join(self.build_tempdir, os.path.basename(self.__crate_path))
        _logger.debug(f"Building in temporary directory {path}")

        os.makedirs(path, exist_ok=True)
        shutil.copytree(self.__crate_path, path, dirs_exist_ok=True)

        build_result = Cargo().build(
            path,
            destination_path=self.extension_path,
            release=release,
        )

        if not build_result.success:
            raise BuildError(f"Failed to build {self.path}")

        checksum_save(self.extension_path, self.dependencies)


all_importables = [
    SingleFileImportable,
    CrateImportable
]


def _check_first_line_contains_rustimport(filepath: str) -> bool:
    with open(filepath, "r") as f:
        return "rustimport" in f.readline()


def get_extension_suffix():
    sysvar = sysconfig.get_config_var  # just an abbreviation for below
    return sysvar("EXT_SUFFIX") or sysvar("SO") or '.so'
