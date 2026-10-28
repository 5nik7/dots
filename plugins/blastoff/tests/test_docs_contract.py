"""Release identity and current-documentation drift checks (history stays history)."""
import re
import unittest
from pathlib import Path
from test_blastoff import core

ROOT=Path(__file__).resolve().parents[1]

class Documentation(unittest.TestCase):
    def test_release_identities_and_commands(self):
        version=(ROOT/'VERSION').read_text().strip()
        self.assertEqual(core.VERSION,version)
        self.assertIn("ModuleVersion = '"+version+"'",(ROOT/'powershell/blastoff.psd1').read_text())
        self.assertIn('blastoff '+version,(ROOT/'man/blastoff.1').read_text().splitlines()[0])
        self.assertIn('## '+version,(ROOT/'CHANGELOG.md').read_text())
        for filename in ('docs/CLI-CONTRACT.md','man/blastoff.1','README.md'):
            text=(ROOT/filename).read_text()
            for command in ('theme edit','theme save','module show','backup delete'):
                self.assertIn(command,text,filename)
            for flag in ('--dry-run','--verbose','--fancy','--fzf','--yes'):
                self.assertIn(flag,text,filename)
            self.assertIn('Ctrl-X',text,filename)
    def test_current_guides_have_no_obsolete_picker_contract(self):
        for filename in ('README.md','docs/CLI-CONTRACT.md','docs/TERMUX-QUICKSTART.md',
                         'docs/TERMINAL-UX.md','docs/INTERACTIVE-CHECKS.md','man/blastoff.1'):
            text=(ROOT/filename).read_text()
            for stale in ('Alt-P','initially hidden','starts hidden','Ambient FZF_* and GUM_*','basic fzf by default','paging/config disabled','config disabled'):
                self.assertNotIn(stale,text,filename)
    def test_helpers_are_within_existing_package_boundary(self):
        for helper in ('operations','provenance','editor','backups','picker_ui','preview'):
            self.assertTrue((ROOT/'lib'/(helper+'.py')).is_file())
        self.assertIn('Native Windows',(ROOT/'docs/STATUS.md').read_text())
