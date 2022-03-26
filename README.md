# rustimport - Import Rust directly from Python! 

<p align=center>
    <a target="_blank" href="https://www.python.org/downloads/" title="Python version"><img src="https://img.shields.io/badge/python-%3E=_3.6-green.svg"></a>
    <!--<a target="_blank" href="https://pypi.org/project/rustimport/" title="PyPI version"><img src="https://img.shields.io/pypi/v/rustimport?logo=pypi"></a>
    <a target="_blank" href="https://pypi.org/project/rustimport/" title="PyPI"><img src="https://img.shields.io/pypi/dm/rustimport"></a>-->
    <a target="_blank" href="LICENSE" title="License: MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg"></a></a>
</p>

rustimport was heavily inspired by and is partly based upon [cppimport](https://github.com/tbenthompson/cppimport). Check it out if you're interested in the same functionality for C and C++!

## Installation

Install with `pip install rustimport`.

## A quick example

Save the Rust code below as `somecode.rs`.
```rust
// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn square(x: i32) -> PyResult<i32> {
    Ok(x * x);
}
```

Then open a Python interpreter and import the Rust extension:

```python
>>> import rustimport.import_hook
>>> import somecode  # This will pause for a moment to compile the module
>>> somecode.square(9)
81
```

Hurray, you've called some Rust code from Python using a combination of `rustimport` and [`pyo3`](https://github.com/PyO3/pyo3)

This workflow enables you to edit both Rust files and Python and recompilation happens automatically and transparently! It's also handy for quickly whipping together an optimized version of a slow Python function.

To easily create a new single-file extension (like above), or a complete crate, use the provided tool:
```bash
$ python3 -m rustimport new my_single_file_extension.rs
# or create a full rust crate:
$ python3 -m rustimport new my_crate
```

And import it from Python:
```python
>>> import rustimport.import_hook
>>> import my_single_file_extension, my_crate
>>> my_single_file_extension.say_hello()
Hello from my_single_file_extension, implemented in Rust!
>>> my_crate.say_hello()
Hello from my_crate, implemented in Rust!
```

Smooth!

## An explanation 

Okay, now that I've hopefully convinced you on how exciting this is, let's get into the details of how to do this yourself. First, the comment at top is essential to opt in to rustimport. Don't forget this! (See below for an explanation of why this is necessary.)
```rust
// rustimport:pyo3
```

The bulk of the file is a generic, simple [pyo3](https://github.com/PyO3/pyo3) extension. We use the `pyo3` crate, then define a simple function that squares `x`, and rustimport takes care of exporting that function as part of a Python extension called `somecode`.

## Templating & Pre-Processing

rustimport offers several layers of customization. This is archieved through a simple pre-processor and templates (well, the only existing template at the moment is `pyo3` - pull requests welcome :D).

### What rustimport did for you in the background
The first example in this Readme is the simplest possible form of using rustimport. You just tell rustimport to use the `pyo3` template by writing `rustimport:pyo3` in the first line, and define a function annotated with `pyo3`'s `#[pyfunction]` macro. In the background, rustimport handled a lot of stuff for you:

1. It set up a minimalistic folder structure for a rust crate with your source code in a temporary location.
2. It generated a Cargo.toml file with the basic configuration for pyo3 and your extension:
```toml
[package]
name = "somecode"
version = "0.1.0"
edition = "2021"

[lib]
name = "somecode"
crate-type = [ "cdylib",]

[dependencies.pyo3]
version = "0.16.2"
features = [ "extension-module",]
```
2. It generated a code block exporting your method and appended it to the end of your file:
```rust
#[pymodule]
fn somecode(_py: Python, m: &PyModule) -> PyResult<()> {
  m.add_function(wrap_pyfunction!(square, m)?)?;
  Ok(())
}
```

### Customizing an extension
You can do all the above yourself. rustimport will detect that and only fill in the missing parts to make your extension work.

#### 1. Extending `Cargo.toml`
For example, to add additional contents to the generated `Cargo.toml` file, use the special `//:` comment syntax at the top of your `.rs` file:
```rust
// rustimport:pyo3

// Set the library's version and add a dependency:
//: [package]
//: version = "1.2.3"
//:
//: [dependencies]
//: rand = "0.8.5"

use rand::Rng;

#[pyfunction]
fn myfunc() {
    println!("{}", rand::thread_rng().gen_range(0..10))
}
```

#### 2.Tracking additional source files
To track additional files for changes, use the special `//d:` comment syntax:
```rust
//d: ../other-folder/somefile.rs
//d: ../*.rs
//d: ./my-directory/**/*.json

// --snip--
```
rustimport will now track files matching these patterns too and re-compiles your extension if any of them changes.

#### 3. Full customization for more control
If you write a more complex extension, it's preferrable to just create a normal Rust crate:
```bash
$ python3 -m rustimport new my_crate
$ tree my_crate
my_crate
├── Cargo.toml
├── .rustimport
└── src
    └── lib.rs
```

The crate contains all necessary configuration to be directly be imported by rustimport and also some additional explanations on how to configure manually.

## Building for production
In production deployments you usually don't want to include the Rust toolchain, all the sources and compile at runtime. Therefore, a simple cli utility for pre-compiling all source files is provided. This utility may, for example, be used in CI/CD pipelines. 

Usage is as simple as

```commandline
python -m rustimport build --release
```

This will build all `*.rs` files and Rust crates in the current directory (and it's subdirectories) if they are eligible to be imported (i.e. contain the `// rustimport` comment in the first line or a `.rustimport` file in case of a crate).

Alternatively, you may specifiy one or more root directories or source files to be built:

```commandline
python -m rustimport build --release ./my/root/folder/ ./my/single/file.rs ./my/crate/
```
_Note: When specifying a path to a file, the header check (`// rustimport`) is skipped for that file._

### Fine-tuning for production
To further improve startup performance for production builds, you can opt-in to skip the checksum and compiled binary existence checks during importing by either setting the environment variable `RUSTIMPORT_RELEASE_MODE` to `true` or setting the configuration from within Python:
```python
rustimport.settings.release_mode = True
```
This essentially just disables the import hook and uses the standard python utilities to import the pre-compiled binary.

**Warning:** Make sure to have all binaries pre-compiled when in release mode, as importing any missing ones will cause exceptions. 

## Frequently asked questions

### What's actually going on?

Sometimes Python just isn't fast enough. Or you have existing code in a Rust crate. So, you write a Python *extension module*, a library of compiled code. I recommend [pyo3](https://github.com/PyO3/pyo3) for Rust to Python bindings.

I discovered that my productivity is slower when my development process goes from *Edit -> Test* in just Python to *Edit -> Compile -> Test* in Python plus Rust. So, `rustimport` combines the process of compiling and importing an extension in Python so that you can just run `import foobar` and not have to worry about multiple steps. Internally, `rustimport` looks for a file `foobar.rs` or a Rust crate (discovered through `foobar/Cargo.toml`). Assuming one is found, the comments at it's beginning are parsed for either a template (`rustimport:pyo3`) or a cargo manifest, then it's compiled and loaded as an extension module.

### Does rustimport recompile every time a module is imported? 
No! Compilation should only happen the first time the module is imported. The Rust source is compared with a checksum on each import to determine if any relevant file has changed. Additional dependencies can be tracked by adding to the header comments:

```rust
//d: ../myothercrate/**/*.rs
//d: ../myothercrate/Cargo.toml
```

By default, rustimport tracks all `*.rs` files as well as `Cargo.toml` and `Cargo.lock` for crates and no additional dependencies for single-file Rust extensions.

### rustimport isn't doing what I want, can I get more verbose output?
`rustimport` uses the standard Python logging tools. Thus, you can enable logging like this:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # or logging.INFO for a bit less verbosity
# ... do some rustimport stuff here
```

### How can I force a rebuild even when the checksum matches?

Set:
```python
rustimport.settings.force_rebuild = True
```
Or set the environment variable `RUSTIMPORT_FORCE_REBUILD` to `true`

And if this is a common occurrence, I would love to hear your use case and why the normal dependency tracking is insufficient!

### Can I use something else than `pyo3`?
Sure! Though I recommend using `pyo3` due to it's simplicity, you're completely free to use any other library, for example [`rust-cpython`](https://github.com/dgrunwald/rust-cpython).

There is an example using `rust-cpython` in [examples/doublecount.rs](./examples/doublecount.rs)

### How can I make compilation faster? 

Compilation happens incrementally by default. That is, the first compilation might take a bit, but subsequent ones are usually much faster.

rustimport uses a temporary directory for caching, which is deleted after a reboot on most systems. Therefore it might be beneficial for you to set a custom cache directory to have a more permanent cache:

```python
rustimport.settings.cache_dir = os.path.realpath("./.rust-cache")
```
Or - you guessed it - use the `RUSTIMPORT_CACHE_DIR` environment variable.

If this directory doesn't exist, it will be created automatically by rustimport.

### Why does the import hook need "rustimport" on the first line of the .rs file?
Modifying the Python import system is a global modification and thus affects all imports from any other package. As a result, when `cppimport` was first implemented, other packages (e.g. `scipy`) suddenly started breaking because import statements internal to those packages were importing C or C++ files instead of the modules they were intended to import. To avoid this failure mode, the import hook uses an "opt in" system where C and C++ files can specify they are meant to be used with cppimport by having a comment on the first line that includes the text "cppimport". 

rustimport has adopted from this and follows the same pattern. Since rustimport also supports importing whole crates, an additional mechanism was necessary to make that work in the same fashion: You can either create a `.rustimport` file in the crate's root folder (next to `Cargo.toml`) or, alternatively, add a `# rustimport` comment to `Cargo.toml`s first line.

As an alternative to the import hook, you can use `imp` or `imp_from_path`. The `rustimport.imp` and `rustimport.imp_from_path` performs exactly the same operation as the import hook but in a slightly more explicit way:
```python
foobar = rustimport.imp("foobar")
foobar = rustimport.imp_from_path("./some/path/foobar.rs")
mycrate = rustimport.imp_from_path("./mycrate/")
```
By default, these explicit function do not require the "rustimport" keyword on the first line of the .rs source file or the according marker in the crate. 

## Contributing and architecture

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on the internals of `rustimport` and how to get involved in development.

## License
rustimport uses the MIT License.
