import importlib.abc
import logging
import sys
import types
from importlib.machinery import ModuleSpec
from typing import Sequence, Optional

from rustimport import settings
from rustimport.find import find_module_importable
from rustimport.importable import Importable, should_rebuild

_logger = logging.getLogger(__name__)


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.__running = False

    def find_spec(
        self, fullname: str, path: Optional[Sequence], target: Optional[types.ModuleType] = ...
    ) -> Optional[ModuleSpec]:
        # Prevent re-entry by the underlying importer
        if self.__running:
            return

        try:
            self.__running = True

            importable = find_module_importable(fullname, opt_in=True)

            if importable is not None:
                return ModuleSpec(
                    name=fullname,
                    loader=Loader(importable),
                )
        except ImportError as e:
            # ImportError should be quashed because that simply means rustimport
            # didn't find anything, and probably shouldn't have found anything!
            _logger.debug(e.msg)
        finally:
            self.__running = False


class Loader(importlib.abc.Loader):
    def __init__(self, importable: Importable):
        self.__importable = importable

    def create_module(self, spec: ModuleSpec) -> Optional[types.ModuleType]:
        if should_rebuild(self.__importable):
            self.__importable.build(release=settings.compile_release_binaries)
        return self.__importable.load()

    def exec_module(self, module: types.ModuleType) -> None:
        pass

    # Deprecated; provided for older python versions:
    def load_module(self, fullname: str) -> types.ModuleType:
        if should_rebuild(self.__importable):
            self.__importable.build(release=settings.compile_release_binaries)
        return self.__importable.load()


if settings.rtld_flags or not settings.release_mode:
    # Add the hook to the list of import handlers for Python.
    sys.meta_path.insert(0, Finder())
