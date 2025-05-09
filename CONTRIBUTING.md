# Contributing 

When contributing to this repository, feel free to add an issue or pull request! There really aren't any rules, but if 
you're mean, I'll be sad. I'm happy to collaborate on pull requests if you would like. There's no need to submit a 
perfect, finished product.

To install in development mode:
```
$ git clone git@github.com:mityax/rustimport.git 
$ cd rustimport
$ python3 -m venv .venv
$ source .venv/bin/activate
(venv) $ pip install -r requirements-development.txt -e .
```

To run the tests:
```
$ python tests/run_all.py
```

## Things to keep in mind
- Please write your commit messages the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#examples) 
  style
- Before making a commit, please run the tests locally (just do a `python tests/run_all.py`)
- Add tests for any new features you contribute to ensure they remain functional in the long run
- If you're not sure whether some contribution is wanted or you need guidance or help in any way to
  get into the project, please create an issue so we can chat!


# Architecture

## Entrypoints:

The main entrypoint for rustimport is the `rustimport.import_hook` module, which interfaces with the Python importing system to allow things like `import myrustfilename`. For a Rust file to be a valid import target, it needs to have the word "rustimport" in its first line, a crate needs to contain either a `.rustimport` file or the word "rustimport" in `Cargo.toml`s first line. Without this constraint, it is possible for the importing system to cause imports in other Python packages to fail. Before adding the first-line constraint, the `cppimport` import_hook had the unfortunate consequence of breaking some scipy modules that had adjacent C and C++ files in the directory tree - thus, `rustimport` adopted the behavior.

There is an alternative, and more explicit interface provided by the `imp`, `imp_from_path`, `build`, `build_filepath` and `build_all` functions here.
* `imp` does exactly what the import hook does except via a function so that instead of `import foomodule` we would do `foomodule = imp('foomodule')`.
* `imp_from_path` is even more explicit, allowing the user to pass a Rust filepath or crate path rather than a modulename. For example, `foomodule = imp('../rustcodedir/foodmodule.rs')`. This is rarely necessary but can be handy for debugging.
* `build` is similar to `imp` except that the library is only built and not actually loaded as a Python module.
* `build_filepath` is similar to `build` except that it allows for specifying a direct filepath, just as `imp_from_path` does.
* `build_all` can be used to build all eligible rust files and crates within a root directory. The method traverses the root directory recursively.

The methods listed above are located in the `__init__.py` to separate external facing API from the guts of the package that live in internal submodules.

They all offer some customization via their keyword arguments.

## What happens when we import a Rust module.

1. First the `rustimport.find.find_module_importable(...)` function is used to find a Rust file that matches the desired module name.
2. Next, we determine if there's already an existing compiled extension that we can use. If there is, the `Importable.needs_rebuild(...)` method is used to determine if the extension is up-to-date with the current code. If the extension is up-to-date, we attempt to load it. If the extension is loaded successfully, we return the module, and we're done! However, if for whichever reason, we can't load an existing extension, we need to build the extension, a process directed by `Importable.build(...)`.
3. The first step of building is to run the Rust file through the preprocessor system using `rust_import.pre_processing.Preprocessor(...)`. This allows users to embed the `Cargo.toml`s contents within a single-file rust extension (via `//: <a-line-of-cargo-toml-code>`), specify additional dependencies to track (via `//d: <file-pattern>`) and use preprocessor-templates (e.g. `// rustimport:pyo3`).
4. Next, we use cargo to build the Rust extension using `rustimport.compiler.Cargo().build(...)`. This function calls the cargo binary with the appropriate arguments to build the extension in place next to the Rust file or crate in the directory tree.
5. Next, we call `rustimport.checksum.save_checksum(...)` to add a hash of the appended contents of all tracked dependency files. This checksum is appended to the end of the `.so` or `.dylib` file. This seems legal according to specifications and, in practice, causes no problems.
6. Finally, the compiled and loaded extension module is returned to the user.

## Useful links

* PEP 302 that made this possible: https://www.python.org/dev/peps/pep-0302/ 
* The gory details of Python importing: https://docs.python.org/3/reference/import.html
