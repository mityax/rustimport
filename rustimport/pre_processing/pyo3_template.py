import re
import sys
from typing import List, Dict, Any

from rustimport.pre_processing.base import Template


class PyO3Template(Template):
    PYO3_VERSION = "0.23.4"

    def process(self) -> Template.TemplatingResult:
        return Template.TemplatingResult(
            cargo_manifest=self.__generate_manifest(),
            contents=self.__process_content(),
            additional_cargo_args=self.__get_cargo_args(),
        )

    def __generate_manifest(self) -> Dict[str, Any]:
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
                'pyo3': {'version': PyO3Template.PYO3_VERSION, 'features': ['extension-module']}
            }
        })

    def __process_content(self) -> bytes:
        if not re.search(rb'#\[pymodule]\s*(?:\w\s+)*?(mod|fn)\s+([\w0-9]+)', self.contents):
            # If the file doesn't contain the "pymodule" macro, we generate it automatically
            return self.contents + b"\n\n" + self.__generate_pymodule()
        return self.contents

    def __generate_pymodule(self) -> bytes:
        # A rather rudimentary implementation of generating PyO3 the "pymodule" macro's contents
        functions = re.finditer(
            rb'#\[pyfunction.*?]\s*'  # the `#[pyfunction]` macro
            rb'((#\[.*?]|//[^\n]*?\n|/\*.*?\*/)\s*)*?'  # any other macros (e.g. `#[pyo3(signature = ...)]`) or comments
            rb'(\w+\s+)*?'  # modifiers such as `pub`
            rb'fn\s+(?P<name>[\w0-9]+)',  # the function declaration
            self.contents, re.MULTILINE | re.DOTALL
        )
        structs = re.finditer(
            rb'#\[pyclass.*?]\s*'  # the `#[pyclass]` macro
            rb'((#\[.*?]|//[^\n]*?\n|/\*.*?\*/)\s*)*?'  # any other macros (e.g. `#[derive(...)]`) or comments
            rb'(\w+\s+)*?'  # modifiers such as `pub`
            rb'(struct|enum)\s+(?P<name>[\w0-9]+)',  # the class/enum declaration
            self.contents, re.MULTILINE | re.DOTALL
        )

        res = [
            b'#[pymodule]',
            b'fn ' + self.lib_name.encode() + b"(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {",
            *[
                b'  m.add_function(wrap_pyfunction!(' + func.group('name') + b', m)?)?;'
                for func in functions
            ],
            *[
                b'  m.add_class::<' + struct.group('name') + b'>()?;'
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
