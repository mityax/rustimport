import re
import sys
from typing import List

from rustimport.pre_processing.base import Template


class PyO3Template(Template):
    def process(self) -> Template.TemplatingResult:
        return Template.TemplatingResult(
            cargo_manifest=self.__generate_manifest(),
            contents=self.__process_content(),
            additional_cargo_args=self.__get_cargo_args(),
        )

    def __generate_manifest(self) -> bytes:
        return self._copy_manifest_with_defaults({
            'package': {
                'name': self.lib_name,
                'version': '0.1.0',
                'edition': '2021',
            },
            'lib': {
                'name': self.lib_name,
                'crate-type': ['cdylib'],
            },
            'dependencies': {
                'pyo3': {'version': '0.16.2', 'features': ['extension-module']}
            }
        })

    def __process_content(self) -> bytes:
        if not re.search(rb'#\[pymodule]\s*(?:\w\s+)*?fn\s+([\w0-9]+)', self.contents):
            # If the file doesn't contain the "pymodule" macro, we generate it automatically
            return self.contents + b"\n\n" + self.__generate_pymodule()

    def __generate_pymodule(self) -> bytes:
        # A rather rudimentary implementation of generating PyO3 the "pymodule" macro's contents
        functions = re.finditer(rb'#\[pyfunction]\s*(?:\w\s+)*?fn\s+([\w0-9]+)', self.contents, re.MULTILINE)
        structs = re.finditer(rb'#\[pyclass]\s*(?:\w\s+)*?(?:struct|enum)\s+([\w0-9]+)', self.contents, re.MULTILINE)

        res = [
            b'#[pymodule]',
            b'fn ' + self.lib_name.encode() + b'(_py: Python, m: &PyModule) -> PyResult<()> {',
            *[
                b'  m.add_function(wrap_pyfunction!(' + func.group(1) + b', m)?)?;'
                for func in functions
            ],
            *[
                b'  m.add_class::<' + struct.group(1) + b'>()?;'
                for struct in structs
            ],
            b'  Ok(())',
            b'}'
        ]

        return b'\n'.join(res)

    def __get_cargo_args(self) -> List[str]:
        args = []
        if sys.platform == "darwin":
            # On macOS, because the extension-module feature disables linking to
            # libpython, some additional linker arguments need to be set.
            # See more: https://pyo3.rs/master/building_and_distribution.html#macos
            args.extend([
                "--",
                "-C", "link-arg=-undefined",
                "-C", "link-arg=dynamic_lookup",
            ])
        return args
