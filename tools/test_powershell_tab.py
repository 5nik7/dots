"""Exercise the native picker with inert completion providers and a test-owned buffer."""
import unittest

import test_powershell_init as fixture


@unittest.skipUnless(fixture.PWSH, 'PowerShell unavailable')
class PowerShellTab(unittest.TestCase):
    setUp = fixture.PowerShellInitTests.setUp
    run_ps = fixture.PowerShellInitTests.run_ps

    def test_exhausted_dots_route_keeps_buffer(self):
        (self.repo / 'bin/dots.ps1').write_text(
            "if (($args -join '|') -eq '__complete|--display-types|files|list|--|') { return }\n"
            "throw 'Incorrect argument context'\n")
        (self.home / 'unrelated-file').touch()
        helpers = fixture.literal(self.repo / 'shells/powershell/helpers.ps1')
        script = r"""
$ErrorActionPreference = 'Stop'
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $env:DOTS 'lib/dots/completion/powershell'))))
Add-Type @'
namespace Microsoft.PowerShell {
    public class PSConsoleReadLine {
        public static void GetBufferState(ref string line, ref int cursor) { line = "dots files list -- "; cursor = line.Length; }
        public static void Replace(int start, int count, string text) { throw new System.Exception("Edited exhausted route"); }
    }
}
'@
function Get-Command { 'Invoke-FixtureFzf' }
function Invoke-FixtureFzf { throw 'Unexpected picker' }
Invoke-DotsFuzzyCompletion
"""
        result = self.run_ps('-Command', f". {helpers}\n" + script, prepare=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_file_colors_duplicate_identity_and_fallback(self):
        helpers = fixture.literal(self.repo / 'shells/powershell/helpers.ps1')
        script = r"""
$ErrorActionPreference = 'Stop'
Add-Type @'
namespace Microsoft.PowerShell {
    public class PSConsoleReadLine {
        public static string Line = "sample ";
        public static bool Fallback;
        public static void TabCompleteNext() { Fallback = true; }
        public static void GetBufferState(ref string line, ref int cursor) { line = Line; cursor = Line.Length; }
        public static void Replace(int start, int count, string text) { Line = Line.Remove(start, count).Insert(start, text); }
    }
}
'@
function Get-Command { if ($global:HasFzf) { 'Invoke-FixtureFzf' } }
function TabExpansion2 {
    $items = foreach ($name in 'one.TXT', 'one.TXT', 'ONE.txt') {
        [Management.Automation.CompletionResult]::new($name, $name, 'ProviderItem', 'fixture description')
    }
    @{ CompletionMatches = $items; ReplacementIndex = 7; ReplacementLength = 0 }
}
function Invoke-FixtureFzf {
    if ('--nth' -notin $args) { throw 'Missing name filter' }
    if ($env:DOTS_COLOR -eq 'always' -and ('--ansi' -notin $args -or '--color=fg+:-1:regular' -notin $args)) {
        throw 'Active row must preserve semantic colors'
    }
    $global:Rows = @($input)
    $global:LASTEXITCODE = 0
    $global:Rows[-1]
}
$global:DotsCompletionStyles = @{enabled='1'; candidate='31'; description='33'; separator='34'}
$env:DOTS_COLOR = 'always'
$env:LS_COLORS = 'di=32:fi=35:*.txt=38;5;88'
$global:HasFzf = $true
$global:LASTEXITCODE = 17
Invoke-DotsFuzzyCompletion
$esc = [char]27
if ($Rows.Count -ne 2 -or -not $Rows[0].Contains("${esc}[38;5;88mone.TXT") -or
    -not $Rows[0].Contains("${esc}[33mfixture description")) { throw "Bad rows: $Rows" }
if ([Microsoft.PowerShell.PSConsoleReadLine]::Line -cne 'sample ONE.txt ' -or $LASTEXITCODE -ne 17) {
    throw 'Insertion identity or exit status changed'
}
[Microsoft.PowerShell.PSConsoleReadLine]::Line = 'sample '
$env:DOTS_COLOR = 'never'
Invoke-DotsFuzzyCompletion
if ($Rows[0].Contains($esc) -or -not $Rows[0].Contains('fixture description')) { throw 'Bad plain rows' }
$global:HasFzf = $false
Invoke-DotsFuzzyCompletion
if (-not [Microsoft.PowerShell.PSConsoleReadLine]::Fallback) { throw 'Missing native fallback' }
"""
        result = self.run_ps('-Command', f". {helpers}\n" + script, prepare=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
