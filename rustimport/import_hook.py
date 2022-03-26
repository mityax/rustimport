import importlib.abc
import logging
import sys
import traceback
import types
from importlib.machinery import ModuleSpec
from typing import Sequence, Optional

from rustimport import settings
from rustimport.find import find_module_importable
from rustimport.importable import Importable

logger = logging.getLogger(__name__)


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

            return ModuleSpec(
                name=fullname,
                loader=Loader(find_module_importable(fullname, opt_in=True)),
            )
        except ImportError:
            # ImportError should be quashed because that simply means rustimport
            # didn't find anything, and probably shouldn't have found anything!
            logger.debug(f"Couldn't find rust module {fullname}: {traceback.format_exc()}")
        finally:
            self.__running = False


class Loader(importlib.abc.Loader):
    def __init__(self, importable: Importable):
        self.__importable = importable

    def load_module(self, fullname: str) -> types.ModuleType:
        if settings.force_rebuild or (not settings.release_mode and self.__importable.needs_rebuild()):
            self.__importable.build()
        return self.__importable.load()


if not settings.release_mode:
    # Add the hook to the list of import handlers for Python.
    sys.meta_path.insert(0, Finder())
