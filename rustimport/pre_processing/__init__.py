import os.path
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Type, Any

import toml

from rustimport.pre_processing.base import merge_cargo_manifests, Template
from rustimport.pre_processing.pyo3_template import PyO3Template


class Preprocessor:
    @dataclass
    class PreprocessorResult:
        cargo_manifest: bytes
        dependency_file_patterns: List[str]
        updated_source: Optional[bytes]
        additional_cargo_args: List[str]

    def __init__(self, path: str, lib_name: str, cargo_manifest_path: Optional[str] = None, workspace_path: Optional[str] = None):
        self.path = path
        self.lib_name = lib_name
        self.cargo_manifest_path = cargo_manifest_path
        self.workspace_path = workspace_path

    def process(self) -> PreprocessorResult:
        with open(self.path, 'rb') as f:
            contents = f.read()

        raw_manifest, template_name, deps = self.__parse_header(contents)
        manifest = toml.loads(raw_manifest.decode())

        if self.cargo_manifest_path is not None:
            with open(self.cargo_manifest_path, 'r') as f:
                manifest = merge_cargo_manifests(toml.load(f), manifest)

        if template_name:
            template = all_templates[template_name.lower()](self.path, self.lib_name, contents, manifest)
            templating_result = template.process()
            manifest = templating_result.cargo_manifest
        else:
            templating_result = None

        self.__process_manifest(manifest)

        return self.PreprocessorResult(
            cargo_manifest=toml.dumps(manifest).encode(),
            dependency_file_patterns=deps,
            updated_source=templating_result.contents if templating_result else None,
            additional_cargo_args=templating_result.additional_cargo_args if templating_result else [],
        )

    @staticmethod
    def __parse_header(contents: bytes) -> Tuple[bytes, Optional[str], List[str]]:
        manifest = b''
        template_name = None
        dependency_file_patterns = []

        if m := re.match(rb'//\s*rustimport(?:\s*:\s*([\w-]+))?$', contents.lstrip().split(b'\n', 1)[0].strip()):
            template_name = m.group(1).decode() if m.group(1) else None

        for line in map(bytes.strip, contents.splitlines()):
            # Break on first non-comment, non-empty line since the header must come before all code:
            if line and not line.strip().startswith(b"//"):
                break
            if line.startswith(b'//:'):
                manifest += line[3:].lstrip() + b'\n'
            elif line.startswith(b'//d:'):
                dependency_file_patterns.append(line[4:].lstrip().decode())
        return manifest, template_name, dependency_file_patterns

    def __process_manifest(self, manifest):
        # Convert relative dependency paths into absolute ones in the manifest, to make them resolvable
        # from the temporary location where the importable is being built:
        root = os.path.dirname(self.cargo_manifest_path or self.path)
        dependency_tables = (
            *_query_dict('dependencies', manifest),
            *_query_dict('dev-dependencies', manifest),
            *_query_dict('build-dependencies', manifest),
            *_query_dict('target.*.dependencies', manifest),
            *_query_dict('target.*.dev-dependencies', manifest),
            *_query_dict('target.*.build-dependencies', manifest),
        )
        for deps in dependency_tables:  # walk through all dependency tables in the manifest
            for spec in deps.values():  # walk through all individual dependency specifications
                if 'path' in spec and not os.path.isabs(spec['path']):
                    abspath = os.path.normpath(os.path.join(root, spec['path']))
                    # If we are in a workspace and the dependency is in the same workspace, there is no need
                    # to make the path absolute; the entire workspace is copied to the temporary directory.
                    if not (self.workspace_path and _path_is_parent(self.workspace_path, abspath)):
                        spec['path'] = abspath



all_templates: Dict[str, Type[Template]] = {
    'pyo3': PyO3Template
}


def _query_dict(query: str, data: dict[str, Any]):
    """
    Retrieves values from a nested dictionary using a dot-separated query with '*' as a wildcard.
    Returns a list of all matching results and an empty list if no matches are found.
    """

    def search(keys, node):
        if not keys:
            return [node]

        key, *rest = keys

        if isinstance(node, dict) and key == '*':
            return [v for child in node.values() for v in search(rest, child)]
        elif isinstance(node, dict) and key in node:
            return search(rest, node[key])
        return []

    return search(query.split("."), data)


def _path_is_parent(parent_path: str, child_path: str):
    # Smooth out relative path names, note: if you are concerned about symbolic links, you should use
    # os.path.realpath too:
    parent_path = os.path.abspath(parent_path)
    child_path = os.path.abspath(child_path)

    # Compare the common path of the parent and child path with the common path of just the parent path. Using the
    # commonpath method on just the parent path will regularise the path name in the same way as the comparison that
    # deals with both paths, removing any trailing path separator:
    return os.path.commonpath([parent_path]) == os.path.commonpath([parent_path, child_path])

