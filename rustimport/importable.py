import abc
import hashlib
import logging
import os.path
import shutil
import sysconfig
import types
from functools import cached_property
from typing import Optional, List, Type, Set

from rustimport import load, BuildError, settings
from rustimport.checksum import is_checksum_valid, save_checksum
from rustimport.compiler import Cargo
from rustimport.error_handling import notify_potential_failure_reason
from rustimport.pre_processing import Preprocessor

_logger = logging.getLogger(__name__)


class Importable(abc.ABC):
    """Abstract interface for importable rust entities"""

    def __init__(self, path: str, fullname: Optional[str] = None):
        self.path = os.path.realpath(path)
        self.fullname = fullname or os.path.splitext(os.path.basename(path))[0]

    @property
    def extension_path(self) -> str:
        return os.path.join(os.path.dirname(self.path), self.name) + get_extension_suffix()

    @property
    def build_tempdir(self) -> str:
        return os.path.join(settings.cache_dir, f'{self.fullname}-{hashlib.md5(self.path.encode()).hexdigest()}')

    @property
    def name(self) -> str:
        return self.fullname.split('.')[-1]

    @property
    def dependencies(self) -> List[str]:
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
                if fullname:
                    notify_potential_failure_reason(
                        f"An importable candidate for the module `{fullname}` was found at {path}, but does "
                        f"not contain the rustimport opt-in comment. If this is the intended importable, "
                        f"either add \"// rustimport\" to it's first line or use "
                        f"`{fullname.split('.')[-1]} = rustimport.imp(\"{fullname}\")` to import the module."
                    )
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
    """
    Importable allowing to import a whole rust crate directory.

    This importable also allows to import crates within a cargo
    workspace – i.e. it handles the according dependencies.
    """

    @property
    def __crate_path(self) -> str:
        return os.path.dirname(self.__manifest_path)

    @property
    def __manifest_path(self) -> str:
        return self.path if self.path.lower().endswith("/cargo.toml") else os.path.join(self.path, 'Cargo.toml')

    @cached_property
    def __workspace_path(self) -> Optional[str]:
        """Returns the path of the cargo workspace this crate belongs to, if there is any."""
        root_dir = os.path.realpath(".").split(os.path.sep)[0] + os.path.sep
        p = self.__crate_path
        while os.path.dirname(p) != root_dir:  # loop through all parent directories...
            p = os.path.dirname(p)

            if os.path.isfile(os.path.join(p, "Cargo.toml")):  # ... and check for a "Cargo.toml" file in each of them.
                return p

        return None

    @property
    def build_tempdir(self) -> str:
        # We overwrite this property in order to return a temporary directory that
        # is specific to the workspace (if any), not to the crate being built. This
        # allows reusing the cache of multiple crates within one workspace.
        # If the crate is not within a workspace, we fall back to the default behaviour.

        if not self.__workspace_path:
            return super().build_tempdir

        return os.path.join(
            settings.cache_dir,
            '{name}-{hash}'.format(
                name=os.path.basename(self.__workspace_path),
                hash=hashlib.md5(self.__workspace_path.encode()).hexdigest(),
            )
        )

    @cached_property
    def dependencies(self) -> List[str]:
        root_path = self.__workspace_path or self.__crate_path
        src_path = os.path.join(self.__crate_path, 'src')

        p = Preprocessor(os.path.join(src_path, 'lib.rs'), lib_name=self.name).process()

        return [
            os.path.join(root_path, '**/*.rs'),
            os.path.join(root_path, '**/Cargo.*'),
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
                if fullname:
                    notify_potential_failure_reason(
                        f"A crate importable candidate for the module `{fullname}` was found at {path}, but "
                        f"it does not contain the rustimport opt-in marker. If this is the intended importable, "
                        f"either add a \".rustimport\" file in the crate's root directory or use "
                        f"`{fullname.split('.')[-1]} = rustimport.imp(\"{fullname}\")` to import it."
                    )
                return None
            return CrateImportable(path=directory, fullname=fullname)

    def build(self, release: bool = False):
        if self.__workspace_path is not None:
            _logger.debug(f"The crate belongs to workspace {self.__workspace_path}")

        root_output_path = self._copy_source_to_build_dir()

        # The full path to the crate, regardless of whether it is within a workspace or not:
        crate_output_subdirectory = os.path.normpath(os.path.join(  # e.g. `/output/path/myworkspace/mycrate` or `/output/path/mycrate`
            root_output_path,
            os.path.relpath(self.__crate_path, self.__workspace_path or self.__crate_path)
        ))

        _logger.debug(f"Building in temporary directory {crate_output_subdirectory}")

        preprocessor_result = self._preprocess(crate_output_subdirectory)

        build_result = Cargo().build(
            crate_output_subdirectory,
            destination_path=self.extension_path,
            release=release,
            additional_args=preprocessor_result.additional_cargo_args,
        )

        if not build_result.success:
            raise BuildError(f"Failed to build {self.path}")

        save_checksum(self.extension_path, self.dependencies, release=release)

    def _copy_source_to_build_dir(self) -> str:
        """
        Copies the source crate or workspace into the temporary build directory
        and return the root path (i.e. to the workspace directory if we're in a
        workspace, to the crate otherwise).

        Note: This method also deletes entities contained in the target directory
              should they appear to no longer be in the source directory.
        """

        src_path = self.__workspace_path or self.__crate_path
        output_path = os.path.join(  # e.g. `/output/path/myworkspace` or `/output/path/mycrate` respectively
            self.build_tempdir,
            os.path.basename(self.__workspace_path or self.__crate_path)
        )

        os.makedirs(output_path, exist_ok=True)

        def ignore(directory: str, names: List[str]) -> Set[str]:
            # Do not copy the root "target" folder as it may be huge and slow:
            return {'target'} if directory in (src_path, output_path) else set()

        # Track the copied files, so we can delete files that are no longer in the source directory:
        copied_files = set()

        def copy_function(src, dst):
            shutil.copy2(src, dst)
            copied_files.add(dst)

        shutil.copytree(src_path, output_path, ignore=ignore, copy_function=copy_function, dirs_exist_ok=True)

        # Delete files that are no longer in the source directory:
        for root, dirs, files in os.walk(output_path, topdown=True):
            dirs[:] = set(dirs) - ignore(root, dirs)  # remove ignored directories from the walk

            for file in files:
                if (abs_path := os.path.join(root, file)) not in copied_files:
                    os.remove(abs_path)

        return output_path

    def _preprocess(self, crate_output_subdirectory: str) -> Preprocessor.PreprocessorResult:
        """
        Calls [Preprocessor.process()] on the crate, updates the source files
        with the result and returns the result for further usage.
        """
        preprocessed = Preprocessor(
            os.path.join(self.__crate_path, 'src/lib.rs'),
            lib_name=self.name,
            cargo_manifest_path=os.path.join(self.__crate_path, 'Cargo.toml'),
        ).process()

        if preprocessed.updated_source is not None:
            with open(os.path.join(crate_output_subdirectory, 'src/lib.rs'), 'wb') as f:
                f.write(preprocessed.updated_source)

        with open(os.path.join(crate_output_subdirectory, 'Cargo.toml'), 'wb') as f:
            f.write(preprocessed.cargo_manifest)

        return preprocessed


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
