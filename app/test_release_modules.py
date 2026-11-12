"""A deferred render import must exist in the standalone package, not only checkout."""
import unittest
from pathlib import Path
from unittest.mock import patch
import build_release


class PackagedImportTests(unittest.TestCase):
    def test_current_runtime_allowlist_closes_over_app_owned_imports(self):
        build_release.validate_modules(Path(__file__).resolve().parents[1])

    def test_missing_deferred_proof_assignment_import_fails_before_build(self):
        modules=[m for m in build_release.MODULES if m!='proof_assignments']
        with patch.object(build_release,'MODULES',modules):
            with self.assertRaisesRegex(ValueError,'proof_assignments'):build_release.validate_modules(Path(__file__).resolve().parents[1])
