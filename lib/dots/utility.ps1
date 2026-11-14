# Lazy native adapter for existing standalone utilities; no startup discovery.
function Invoke-DotsUtility {
    param([string]$Root, [string]$Name, [string[]]$Arguments)
    . (Join-Path $Root 'lib/dots/files/entry.ps1')
    $previous = $env:DOTS_UTILITY_PWD
    $oldTransport = $env:DOTS_UTILITY_TRANSPORT
    try {
        $env:DOTS_UTILITY_PWD = $PWD.ProviderPath
        if ($Name -eq 'fzopt') {
            $env:DOTS_UTILITY_TRANSPORT = 'powershell'
            $output = Invoke-DotsFiles $Root utility (@($Name) + $Arguments)
            $code = $script:DotsFilesExitCode
            if ($code -eq 0 -and $output) {
                $result = ($output -join "`n") | ConvertFrom-Json
                if ($null -ne $result.environment) { $env:FZF_DEFAULT_OPTS = [string]$result.environment }
                if ($result.output) {
                    # Keep the success stream capturable/redirectable like the
                    # native controller; Write-Output supplies the final newline.
                    $text = [string]$result.output
                    if ($text.EndsWith("`n")) { $text = $text.Substring(0, $text.Length - 1) }
                    Write-Output -InputObject $text
                }
            }
        } else {
            Invoke-DotsFiles $Root utility (@($Name) + $Arguments)
            $code = $script:DotsFilesExitCode
        }
    } finally {
        $env:DOTS_UTILITY_PWD = $previous
        $env:DOTS_UTILITY_TRANSPORT = $oldTransport
    }
    $global:LASTEXITCODE = $code
}
