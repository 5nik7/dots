function Get-GitHubUserRepo {
    <#
        .Synopsis
        Download GitHub User Gists & Repositories using REST API and ConcurrentQueue collections for improved performance

        .DESCRIPTION
        Uses git.exe to clone the gists and repositories of a github user.
        You can filter repositories by name and language.
        -Exclude parameter will exclude any repositories that match the string/strings listed.
        To filter by programming language use FilterByLanguage to enable the filter by language feature
        then use the -Languages parameter to list the programming languages you want downloaded

        Requires git.exe

        .PARAMETER UserName
        The name of the user whose repositories are to be downloaded

        .PARAMETER Path
        Directory where the user's repositories are to be downloaded.
        Repositories are downlaoded to $Path\GITHUB_USERNAME\REPOSITORY_NAME

        .PARAMETER Exclude
        Exclude repositories whose names match the string/strings defined with -Exclude

        .PARAMETER ThrottleLimit
        Specifies the number of script blocks to clone a specific repository that run in parallel.  The default value is 5.

        .PARAMETER FilterByLanguage
        When this switch is used it will filter repositories who language is not specified in the -Languages parameter.

        .PARAMETER Languages
        The languages to filter repositories for when FilterByLanguage switch is used.

        .PARAMETER Token
        GitHub API token.  If not set, function checks for env:GITHUB_TOKEN and uses that for the Token parameter if it exists.

        .EXAMPLE
        Get-GitHubUserRepo -UserName WozNet -Path 'V:\git\users' -Exclude 'docs'

        .EXAMPLE
        'WozNet','PowerShell','Microsoft' | Get-GitHubUserRepo -Path 'V:\git\users' -Exclude 'azure,'office365'
    #>
    [CmdletBinding()]
    [Alias('dlgit')]
    param(
        [Parameter(Mandatory, ValueFromPipeline, HelpMessage = 'GitHub UserName')]
        [String[]]$UserName,

        [Parameter(HelpMessage = 'Directory to save User Gists and Repositories')]
        [ValidateScript({Test-Path -Path $_ -PathType Container})]
        [String]$Path = 'D:\vlab\git\users',

        [Parameter(HelpMessage = 'Exclude Repositories with Names matching these strings')]
        [String[]]$Exclude = @('docs'),

        [Parameter(HelpMessage = 'ThrottleLimit for ConcurrentQueue parallel processing')]
        [int]$ThrottleLimit = 5,

        [Parameter(HelpMessage = 'Filters repository by language, only repos with the specified programming languages will be cloned')]
        [switch]$FilterByLanguage,

        [Parameter(HelpMessage = 'Programming languages to download when FilterByLanguage is enabled, repos with other programming languages will be excluded')]
        [string[]]$Languages = @('PowerShell', 'C#'),

        [Parameter(HelpMessage = 'GitHub Api token')]
        [string]$Token
    )
    Begin {
        if (-not $Token) {
            Write-Verbose 'Token parameter was not set, check for env var env:GITHUB_TOKEN'
            if ($env:GITHUB_TOKEN) {
                Write-Verbose 'env:GITHUB_TOKEN was found. Setting Token parameter to env:GITHUB_TOKEN'
                $Token = $env:GITHUB_TOKEN
            }
        }

        [System.IO.Path]::Combine($PSScriptRoot, '..\Private') | Get-ChildItem | ForEach-Object { . $PSItem.FullName }
        $HtmlFile = [System.IO.Path]::Combine($PSScriptRoot, '..\Lib\show-gists-template.html') | Get-Item
        $HTML = [System.IO.File]::ReadAllText($HtmlFile)

        if (-not [System.IO.Path]::IsPathRooted($Path)) {
            Write-Warning 'Odd errors when -Path parameter is not a rooted path.'
            Write-Warning ('Attempting to get complete path using [System.IO.Path]::GetFullPath({0}).' -f $Path)
            $Path = [System.IO.Path]::GetFullPath($Path)
        }

        if ($Token) {
            $PSDefaultParameterValues.GetEnumerator().Where({ $_.Key -match 'GitHubApi' }).ForEach({ $PSDefaultParameterValues.Remove($_.Key) })
            $PSDefaultParameterValues.Add('Get-GitHubApi*:Token', $Token)
        }

        Push-Location -Path $PWD.ProviderPath -StackName 'StartingPath'
        Push-Location -Path $Path

        try {
            if (-not (Get-Command -Name git.exe)) { throw 'git.exe is missing' }
        }
        catch {
            Write-CustomError -ErrorRecord $_
            throw $_
        }

        $UserPathList = [System.Collections.Generic.List[string]]@()
        $StopWatch = [System.Diagnostics.Stopwatch]::New()
        $StopWatch.Start()
        $Count = 0
        $StartTime = [datetime]::Now
    }
    Process {
        # Download
        foreach ($GitUser in $UserName) {
            $Count++
            Write-MyProgress -StartTime $StartTime -Object $UserName -Count $Count

            $UserPath = [System.IO.Path]::Combine($Path, $GitUser)
            $UserPathList.Add($UserPath)

            if (-not (Test-Path -Path $UserPath)) { $null = New-Item -Path $UserPath -ItemType Directory }
            Push-Location -Path $UserPath -StackName UserPath

            # Update GitHub repo using in each existing repo - git pull --all
            Get-ChildItem -Directory -Path $UserPath -Exclude '_gist' | Invoke-InDirectory -ScriptBlock {
                if (Test-Path -Path .git) { $null = git pull --all *>&1 }
            }

            #region - Get Gist
            $UserGist = Get-GitHubApiGist -UserName $GitUser
            if ($UserGist) {
                $GistDir = [System.IO.Path]::Combine($UserPath, '_gist')
                $TempGistDir = [System.IO.Path]::Combine($UserPath, '_tempgist')
                if (-not (Test-Path -Path $GistDir)) { $null = New-Item -Path $GistDir -ItemType Directory }
                if (-not (Test-Path -Path $TempGistDir)) { $null = New-Item -Path $TempGistDir -ItemType Directory }

                Get-ChildItem -Path $GistDir | Remove-Item -Recurse -Force
                Set-Content -Value ($HTML.Replace('---', $GitUser)) -Path ([System.IO.Path]::Combine($UserPath, '_gist.html')) -Force
                Write-Output ('{2}{0} Gists - {1}' -f $GitUser, $UserGist.Count, ("`n"))

                Push-Location -Path $TempGistDir

                #region Gist - ConcurrentQueue
                $ConcurrentQueue = [System.Collections.Concurrent.ConcurrentQueue[object]]::new()
                $UserGist | ForEach-Object { $ConcurrentQueue.Enqueue($_) }

                # Start processing ConcurrentQueue collection
                $null = 1..$ThrottleLimit | ForEach-Object {
                    Start-ThreadJob {
                        $i = $null
                        while ($args[0].Count -gt 0) {
                            if ($args[0].TryDequeue([ref]$i)) {
                                ###########################################################################

                                $UGist = $i
                                $StartProcesParams = @{
                                    FilePath = 'git.exe'
                                    ArgumentList = ('clone --recursive {0}' -f $UGist.git_pull_url)
                                    WindowStyle = 'Hidden'
                                    Wait = $true
                                }
                                Start-Process @StartProcesParams
                                $UGistDir = Join-Path -Path $using:TempGistDir -ChildPath $UGist.id
                                (
                                    (Join-Path -Path $UGistDir -ChildPath . -Resolve),
                                    (Join-Path -Path $UGistDir -ChildPath * -Resolve)
                                ) | Get-Item | ForEach-Object {
                                    Write-Verbose ('Changing LastWriteTime to Gist updated_at value - {0}' -f $_.Name)
                                    $_.LastWriteTime = $UGist.updated_at
                                }
                                $UGist, $UGistDir = $null
                                Start-Sleep -Milliseconds 50

                                ###########################################################################
                            }
                        }
                    } -ArgumentList $ConcurrentQueue
                } | Wait-Job

                #endregion Gist - ConcurrentQueue

                ### Delete .git folders from cloned gist
                Get-ChildItem -Path $TempGistDir | ForEach-Object { Join-Path -Path $_ -ChildPath '.git' -Resolve } | Remove-Item -Recurse -Force

                ### Start Moving Gist from temp dir to $GistDir
                Get-ChildItem -Path $TempGistDir | ForEach-Object {
                    $TGDir = $_
                    $TGFiles = $TGDir | Get-ChildItem -Force:$false
                    if ($TGFiles.Count -eq 1) {
                        try {
                            $TGFiles | Move-Item -Destination $GistDir -PassThru:$false -ErrorAction Stop
                        }
                        catch [System.IO.IOException] {
                            'Shit happened! Attempting to rename and try moving again - {0}' -f $TGFiles.Name | Write-Warning
                            $TGFRenamed = $TGFiles | Rename-Item -NewName { $_.Name.Replace($_.BaseName, ('{0}-{1}' -f $_.BaseName, $_.Directory.Name.Substring(0, 6))) } -PassThru
                            $TGFRenamed | Move-Item -Destination $GistDir -PassThru:$false -ErrorAction Stop
                        }
                        $MCheck = $TGDir | Get-ChildItem -Force:$false
                        if ($MCheck.Count -eq 0) { Remove-Item -Path $TGDir -Recurse -Force }
                        else { Write-Warning ('{0} is not empty.{1}Files left - {2}' -f $TGDir.Name, "`n", $MCheck.Count) }
                    }
                    else {
                        try {
                            $TGDir | Move-Item -Destination $GistDir -PassThru:$false -ErrorAction Stop
                        }
                        catch [System.IO.IOException] {
                            Write-Error $_
                        }
                    }
                }
                Pop-Location -StackName UserPath
                ### Cleaning up Temp Gist Dir
                Remove-Item -Path $TempGistDir -Recurse -Force
            }
            #endregion - Get Gist

            #region - Get Repo
            Push-Location -Path $UserPath
            $FilteredUserRepo = $UserRepo = Get-GitHubApiRepository -UserName $GitUser

            if ($Exclude) {
                $FilteredUserRepo = $FilteredUserRepo.Where({ $_.name -notmatch ($Exclude -join '|') })
            }
            if ($FilterByLanguage) {
                $FilteredUserRepo = $FilteredUserRepo.Where({ ($_ | Get-GitHubApiRepositoryLanguage).psobject.Properties.Name -match ($Languages -join '|') })
            }

            $FilteredRepos = Compare-Object -ReferenceObject $UserRepo.name -DifferenceObject $FilteredUserRepo.name -PassThru

            [pscustomobject]@{
                User = $GitUser
                Repo2Clone = $FilteredUserRepo.Count
                Excluded = $FilteredRepos -join ', '
            } | Format-List | Out-String

            $FilteredUserRepo | Format-Wide -Property @{e = { if ($_.name.Length -gt 27) { $_.name.Substring(0, 24) + '...' } else { $_.name } } } -AutoSize

            #region Repo - ConcurrentQueue
            $ConcurrentQueue = [System.Collections.Concurrent.ConcurrentQueue[object]]::new()
            $FilteredUserRepo | ForEach-Object { $ConcurrentQueue.Enqueue($_) }

            # Start processing ConcurrentQueue collection
            $null = 1..$ThrottleLimit | ForEach-Object {
                Start-ThreadJob {
                    $i = $null
                    while ($args[0].Count -gt 0) {
                        if ($args[0].TryDequeue([ref]$i)) {
                            ###########################################################################

                            $URepo = $i
                            $StartProcesParams = @{
                                FilePath = 'git.exe'
                                ArgumentList = ('clone --checkout --recurse-submodules {0}' -f $URepo.clone_url)
                                WindowStyle = 'Hidden'
                                Wait = $true
                            }
                            Start-Process @StartProcesParams

                            Start-Sleep -Milliseconds 50

                            $RepoUpdatedDate = $URepo.updated_at
                            $RepoDir = Join-Path -Path $using:UserPath -ChildPath $URepo.name -Resolve | Get-Item
                            $RepoFiles = $RepoDir | Get-ChildItem -Recurse -Force:$false -ErrorAction SilentlyContinue
                            $RepoDir.LastWriteTime = $RepoUpdatedDate
                            $RepoFiles.ForEach({ $_.LastWriteTime = $RepoUpdatedDate })

                            ###########################################################################
                        }
                    }
                } -ArgumentList $ConcurrentQueue
            } | Wait-Job

            #endregion Repo - ConcurrentQueue

            ################################################################
            #endregion - Get Repo
        }
    }
    End {
        Write-MyProgress -Completed
        $StopWatch.Stop()
        'Time - {0:m\:ss}{1}' -f $StopWatch.Elapsed, ("`n")
        'Updated User Directories:'
        $UserPathList

        Pop-Location -StackName StartingPath
    }
}
