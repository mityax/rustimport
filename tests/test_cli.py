import os
import sys
import tempfile
import unittest
from subprocess import Popen
from typing import Optional

from rustimport.importable import SingleFileImportable, CrateImportable


class CLITestCase(unittest.TestCase):
    """
    This test case tests basic aspects of the two major cli
    functionalities – `new` and `build`
    """

    ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
    POPEN_BASE = [sys.executable, os.path.join(ROOT_DIR, 'rustimport/__main__.py')]

    def test_singlefile(self):
        with tempfile.TemporaryDirectory(suffix='-rustimport-test-singlefile') as directory:
            filename = 'singlefile.rs'

            # Create a new extension and check exit code & output file:
            new = self.__run("new", filename, cwd=directory)
            self.assertEqual(new.wait(), 0)
            self.assertTrue(os.path.isfile(os.path.join(directory, filename)))

            # Build and check exit code:
            build = self.__run("build", filename, cwd=directory)
            self.assertEqual(build.wait(), 0)

            # Check whether compiled extension exists:
            importable = SingleFileImportable(os.path.join(directory, filename), filename[:-3])
            self.assertTrue(os.path.isfile(importable.extension_path))

    def test_crate(self):
        with tempfile.TemporaryDirectory(suffix='-rustimport-test-crate') as directory:
            crate_name = 'crate_a'

            # Create a new extension and check exit code & output file:
            new = self.__run("new", crate_name, cwd=directory)
            self.assertEqual(new.wait(), 0)
            self.assertTrue(os.path.isfile(os.path.join(directory, crate_name, ".rustimport")))
            self.assertTrue(os.path.isfile(os.path.join(directory, crate_name, "Cargo.toml")))
            self.assertTrue(os.path.isfile(os.path.join(directory, crate_name, "src/lib.rs")))

            # Build and check exit code:
            build = self.__run("build", crate_name, cwd=directory)
            self.assertEqual(build.wait(), 0)

            # Check whether compiled extension exists:
            importable = CrateImportable(os.path.join(directory, crate_name), crate_name)
            self.assertTrue(os.path.isfile(importable.extension_path))

    def test_build_all(self):
        # The directory tree should look roughly like this after the test is complete:
        #
        # ├── invalid_crate
        # │   ├── Cargo.toml
        # │   └── src
        # │       └── lib.rs
        # ├── invalid_importable.rs
        # ├── other
        # │   └── path
        # │       └── to
        # │           ├── crate_b
        # │           │   ├── Cargo.toml
        # │           │   └── src
        # │           │       └── lib.rs
        # │           └── crate_b.cpython-311-x86_64-linux-gnu.so
        # ├── path
        # │   └── to
        # │       ├── crate_a
        # │       │   ├── Cargo.toml
        # │       │   └── src
        # │       │       └── lib.rs
        # │       └── crate_a.cpython-311-x86_64-linux-gnu.so
        # ├── singlefile_a.cpython-311-x86_64-linux-gnu.so
        # └── singlefile_a.rs
        
        with tempfile.TemporaryDirectory(suffix='-rustimport-test-build-all') as tempdir:
            importables_to_create = [
                "singlefile_a.rs",
                "path/to/crate_a",
                "other/path/to/crate_b",
            ]

            # create all the importables using the cli
            for pth in importables_to_create:
                directory, importable_name = os.path.split(pth)
                os.makedirs(os.path.join(tempdir, directory), exist_ok=True)
                new = self.__run("new", importable_name, cwd=os.path.join(tempdir, directory))
                self.assertEqual(new.wait(), 0)

            # Create two mock importables (singlefile and crate), that'll fail if they're tried to be built, to assess
            # whether rustimport correctly ignores importables not containing the marker.
            with open(os.path.join(tempdir, 'invalid_importable.rs'), "w+") as f:
                f.write("Not marked as an importable! If anyone tries to compile this, it'll fail dramatically!")
            os.makedirs(os.path.join(tempdir, "invalid_crate/src"))
            with open(os.path.join(tempdir, "invalid_crate/Cargo.toml"), "w+") as f:
                f.write("Not marked as an importable! If anyone tries to compile this, it'll fail dramatically!")
            with open(os.path.join(tempdir, "invalid_crate/src/lib.rs"), "w+") as f:
                f.write("Not marked as an importable! If anyone tries to compile this, it'll fail dramatically!")

            # Build all and check exit code:
            build = self.__run("build", ".", cwd=tempdir)
            self.assertEqual(build.wait(), 0)

            # Check whether compiled extensions exists:
            for pth in importables_to_create:
                if pth.endswith(".rs"):
                    importable = SingleFileImportable(os.path.join(tempdir, pth), os.path.basename(pth)[:-3])
                else:
                    importable = CrateImportable(os.path.join(tempdir, pth), os.path.basename(pth))
                self.assertTrue(os.path.isfile(importable.extension_path))

    def test_debug_and_release_builds(self):
        with tempfile.TemporaryDirectory(suffix='-rustimport-test-debug-and-release-builds') as directory:
            filename = 'singlefile.rs'

            # Create a new extension and check exit code & output file:
            new = self.__run("new", filename, cwd=directory)
            self.assertEqual(new.wait(), 0)
            self.assertTrue(os.path.isfile(os.path.join(directory, filename)))

            # Build in debug mode and check exit code:
            build = self.__run("build", filename, cwd=directory)
            self.assertEqual(build.wait(), 0)

            # Check whether compiled extension exists and is valid:
            importable = SingleFileImportable(os.path.join(directory, filename), filename[:-3])
            self.assertTrue(os.path.isfile(importable.extension_path))
            self.assertFalse(importable.needs_rebuild(release=False))
            self.assertTrue(importable.needs_rebuild(release=True))

            # Build in release mode and check exit code:
            build = self.__run("build", "--release", filename, cwd=directory)
            self.assertEqual(build.wait(), 0)
            self.assertTrue(importable.needs_rebuild(release=False))
            self.assertFalse(importable.needs_rebuild(release=True))

    @staticmethod
    def __run(*args, cwd: Optional[str] = None) -> Popen:
        proc = Popen(
            CLITestCase.POPEN_BASE + list(args),
            cwd=cwd,
        )
        return proc


if __name__ == '__main__':
    unittest.main()
