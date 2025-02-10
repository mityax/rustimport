import abc
import copy
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Dict, Any, List


class Template(abc.ABC):
    @dataclass
    class TemplatingResult:
        cargo_manifest: Dict[str, Any]
        contents: bytes
        additional_cargo_args: List[str]

    def __init__(self, path: str, lib_name: str, contents: bytes, cargo_manifest: Dict[str, Any]):
        self.path = path
        self.lib_name = lib_name
        self.contents = contents
        self.cargo_manifest = cargo_manifest

    @abc.abstractmethod
    def process(self) -> TemplatingResult:
        raise NotImplemented

    def _copy_manifest_with_defaults(self, defaults: Mapping[str, Any]) -> Dict[str, Any]:
        return merge_cargo_manifests(self.cargo_manifest, defaults)


def merge_cargo_manifests(a: MutableMapping[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges manifest `b` into manifest `a` (i.e. `b` provides default values that `a` overrides)
    and returns the merged manifest.

    This function returns a new manifest and does not modify its input manifests.
    """
    return _recursive_setdefault(copy.deepcopy(a), b)  # noqa


def _recursive_setdefault(mapping: MutableMapping[str, Any], defaults: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """
    Recursively merge all items in `default` that do not exist in `mapping` into it. This modifies
    the original `mapping`argument, but not `defaults`.
    """
    for k, v in defaults.items():
        if k in mapping and not isinstance(mapping[k], MutableMapping):
            continue
        elif isinstance(v, MutableMapping):
            mapping[k] = _recursive_setdefault(mapping.get(k, {}), v)
        else:
            mapping[k] = v
    return mapping
