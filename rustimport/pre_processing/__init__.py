import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Type

from rustimport.pre_processing.base import merge_cargo_manifests, Template
from rustimport.pre_processing.pyo3_template import PyO3Template


class Preprocessor:
    @dataclass
    class PreprocessorResult:
        cargo_manifest: bytes
        dependency_file_patterns: List[str]
        updated_source: Optional[bytes]
        additional_cargo_args: List[str]

    def __init__(self, path: str, lib_name: str, cargo_manifest_path: Optional[str] = None):
        self.path = path
        self.lib_name = lib_name
        self.cargo_manifest_path = cargo_manifest_path

    def process(self) -> PreprocessorResult:
        with open(self.path, 'rb') as f:
            contents = f.read()

        manifest, template_name, deps = self.__parse_header(contents)

        if self.cargo_manifest_path is not None:
            with open(self.cargo_manifest_path, 'rb') as f:
                if manifest.strip():
                    manifest = merge_cargo_manifests(f.read(), manifest)
                else:
                    manifest = f.read()

        if template_name:
            template = all_templates[template_name.lower()](self.path, self.lib_name, contents, manifest)
            templating_result = template.process()
        else:
            templating_result = None

        return self.PreprocessorResult(
            cargo_manifest=templating_result.cargo_manifest if templating_result else manifest,
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
        return manifest + b'\n', template_name, dependency_file_patterns


all_templates: Dict[str, Type[Template]] = {
    'pyo3': PyO3Template
}
