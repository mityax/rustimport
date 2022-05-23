import abc
import typing
from dataclasses import dataclass

import toml


class Template(abc.ABC):
    @dataclass
    class TemplatingResult:
        cargo_manifest: bytes
        contents: bytes
        additional_cargo_args: typing.List[str]

    def __init__(self, path: str, lib_name: str, contents: bytes, cargo_manifest: bytes):
        self.path = path
        self.lib_name = lib_name
        self.contents = contents
        self.cargo_manifest = cargo_manifest

    @abc.abstractmethod
    def process(self) -> TemplatingResult:
        raise NotImplemented

    def _copy_manifest_with_defaults(self, defaults: typing.MutableMapping) -> bytes:
        return merge_cargo_manifests(defaults, self.cargo_manifest)


def merge_cargo_manifests(a: typing.Union[bytes, typing.Mapping], b: typing.Union[bytes, typing.Mapping]) -> bytes:
    return toml.dumps(_recursive_setdefault(
        toml.loads(b.decode()) if isinstance(b, bytes) else b,
        toml.loads(a.decode()) if isinstance(a, bytes) else a,
    )).encode()


def _recursive_setdefault(original: typing.MutableMapping, defaults: typing.MutableMapping):
    for k, v in defaults.items():
        if k in original and not isinstance(original[k], typing.MutableMapping):
            continue
        elif isinstance(v, typing.MutableMapping):
            original[k] = _recursive_setdefault(original.get(k, {}), v)
        else:
            original[k] = v
    return original
