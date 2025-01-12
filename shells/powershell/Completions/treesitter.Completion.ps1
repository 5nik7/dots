
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'tree-sitter' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'tree-sitter'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'tree-sitter' {
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('init-config', 'init-config', [CompletionResultType]::ParameterValue, 'Generate a default config file')
            [CompletionResult]::new('init', 'init', [CompletionResultType]::ParameterValue, 'Initialize a grammar repository')
            [CompletionResult]::new('generate', 'generate', [CompletionResultType]::ParameterValue, 'Generate a parser')
            [CompletionResult]::new('build', 'build', [CompletionResultType]::ParameterValue, 'Compile a parser')
            [CompletionResult]::new('parse', 'parse', [CompletionResultType]::ParameterValue, 'Parse files')
            [CompletionResult]::new('test', 'test', [CompletionResultType]::ParameterValue, 'Run a parser''s tests')
            [CompletionResult]::new('fuzz', 'fuzz', [CompletionResultType]::ParameterValue, 'Fuzz a parser')
            [CompletionResult]::new('query', 'query', [CompletionResultType]::ParameterValue, 'Search files using a syntax tree query')
            [CompletionResult]::new('highlight', 'highlight', [CompletionResultType]::ParameterValue, 'Highlight a file')
            [CompletionResult]::new('tags', 'tags', [CompletionResultType]::ParameterValue, 'Generate a list of tags')
            [CompletionResult]::new('playground', 'playground', [CompletionResultType]::ParameterValue, 'Start local playground for a parser in the browser')
            [CompletionResult]::new('dump-languages', 'dump-languages', [CompletionResultType]::ParameterValue, 'Print info about all known language parsers')
            [CompletionResult]::new('complete', 'complete', [CompletionResultType]::ParameterValue, 'Generate shell completions')
            break
        }
        'tree-sitter;init-config' {
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;init' {
            [CompletionResult]::new('-u', '-u', [CompletionResultType]::ParameterName, 'Update outdated files')
            [CompletionResult]::new('--update', '--update', [CompletionResultType]::ParameterName, 'Update outdated files')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;generate' {
            [CompletionResult]::new('--abi', '--abi', [CompletionResultType]::ParameterName, 'Select the language ABI version to generate (default 14). Use --abi=latest to generate the newest supported version (14).')
            [CompletionResult]::new('--libdir', '--libdir', [CompletionResultType]::ParameterName, 'The path to the directory containing the parser library')
            [CompletionResult]::new('--report-states-for-rule', '--report-states-for-rule', [CompletionResultType]::ParameterName, 'Produce a report of the states for the given rule, use `-` to report every rule')
            [CompletionResult]::new('--js-runtime', '--js-runtime', [CompletionResultType]::ParameterName, 'The name or path of the JavaScript runtime to use for generating parsers')
            [CompletionResult]::new('-l', '-l', [CompletionResultType]::ParameterName, 'Show debug log during generation')
            [CompletionResult]::new('--log', '--log', [CompletionResultType]::ParameterName, 'Show debug log during generation')
            [CompletionResult]::new('--no-bindings', '--no-bindings', [CompletionResultType]::ParameterName, 'Deprecated (no-op)')
            [CompletionResult]::new('-b', '-b', [CompletionResultType]::ParameterName, 'Compile all defined languages in the current dir')
            [CompletionResult]::new('--build', '--build', [CompletionResultType]::ParameterName, 'Compile all defined languages in the current dir')
            [CompletionResult]::new('-0', '-0', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('--debug-build', '--debug-build', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;build' {
            [CompletionResult]::new('-o', '-o', [CompletionResultType]::ParameterName, 'The path to output the compiled file')
            [CompletionResult]::new('--output', '--output', [CompletionResultType]::ParameterName, 'The path to output the compiled file')
            [CompletionResult]::new('-w', '-w', [CompletionResultType]::ParameterName, 'Build a WASM module instead of a dynamic library')
            [CompletionResult]::new('--wasm', '--wasm', [CompletionResultType]::ParameterName, 'Build a WASM module instead of a dynamic library')
            [CompletionResult]::new('-d', '-d', [CompletionResultType]::ParameterName, 'Run emscripten via docker even if it is installed locally (only if building a WASM module with --wasm)')
            [CompletionResult]::new('--docker', '--docker', [CompletionResultType]::ParameterName, 'Run emscripten via docker even if it is installed locally (only if building a WASM module with --wasm)')
            [CompletionResult]::new('--reuse-allocator', '--reuse-allocator', [CompletionResultType]::ParameterName, 'Make the parser reuse the same allocator as the library')
            [CompletionResult]::new('-0', '-0', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('--debug', '--debug', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;parse' {
            [CompletionResult]::new('--paths', '--paths', [CompletionResultType]::ParameterName, 'The path to a file with paths to source file(s)')
            [CompletionResult]::new('--scope', '--scope', [CompletionResultType]::ParameterName, 'Select a language by the scope instead of a file extension')
            [CompletionResult]::new('--timeout', '--timeout', [CompletionResultType]::ParameterName, 'Interrupt the parsing process by timeout (µs)')
            [CompletionResult]::new('--edits', '--edits', [CompletionResultType]::ParameterName, 'Apply edits in the format: "row, col delcount insert_text"')
            [CompletionResult]::new('--encoding', '--encoding', [CompletionResultType]::ParameterName, 'The encoding of the input files')
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-n', '-n', [CompletionResultType]::ParameterName, 'Parse the contents of a specific test')
            [CompletionResult]::new('--test-number', '--test-number', [CompletionResultType]::ParameterName, 'Parse the contents of a specific test')
            [CompletionResult]::new('-d', '-d', [CompletionResultType]::ParameterName, 'Show parsing debug log')
            [CompletionResult]::new('--debug', '--debug', [CompletionResultType]::ParameterName, 'Show parsing debug log')
            [CompletionResult]::new('-0', '-0', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('--debug-build', '--debug-build', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('-D', '-D ', [CompletionResultType]::ParameterName, 'Produce the log.html file with debug graphs')
            [CompletionResult]::new('--debug-graph', '--debug-graph', [CompletionResultType]::ParameterName, 'Produce the log.html file with debug graphs')
            [CompletionResult]::new('--wasm', '--wasm', [CompletionResultType]::ParameterName, 'Compile parsers to wasm instead of native dynamic libraries')
            [CompletionResult]::new('--dot', '--dot', [CompletionResultType]::ParameterName, 'Output the parse data with graphviz dot')
            [CompletionResult]::new('-x', '-x', [CompletionResultType]::ParameterName, 'Output the parse data in XML format')
            [CompletionResult]::new('--xml', '--xml', [CompletionResultType]::ParameterName, 'Output the parse data in XML format')
            [CompletionResult]::new('-s', '-s', [CompletionResultType]::ParameterName, 'Show parsing statistic')
            [CompletionResult]::new('--stat', '--stat', [CompletionResultType]::ParameterName, 'Show parsing statistic')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('--time', '--time', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('--open-log', '--open-log', [CompletionResultType]::ParameterName, 'Open `log.html` in the default browser, if `--debug-graph` is supplied')
            [CompletionResult]::new('-r', '-r', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('--rebuild', '--rebuild', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('--no-ranges', '--no-ranges', [CompletionResultType]::ParameterName, 'Omit ranges in the output')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;test' {
            [CompletionResult]::new('-i', '-i', [CompletionResultType]::ParameterName, 'Only run corpus test cases whose name matches the given regex')
            [CompletionResult]::new('--include', '--include', [CompletionResultType]::ParameterName, 'Only run corpus test cases whose name matches the given regex')
            [CompletionResult]::new('-e', '-e', [CompletionResultType]::ParameterName, 'Only run corpus test cases whose name does not match the given regex')
            [CompletionResult]::new('--exclude', '--exclude', [CompletionResultType]::ParameterName, 'Only run corpus test cases whose name does not match the given regex')
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-u', '-u', [CompletionResultType]::ParameterName, 'Update all syntax trees in corpus files with current parser output')
            [CompletionResult]::new('--update', '--update', [CompletionResultType]::ParameterName, 'Update all syntax trees in corpus files with current parser output')
            [CompletionResult]::new('-d', '-d', [CompletionResultType]::ParameterName, 'Show parsing debug log')
            [CompletionResult]::new('--debug', '--debug', [CompletionResultType]::ParameterName, 'Show parsing debug log')
            [CompletionResult]::new('-0', '-0', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('--debug-build', '--debug-build', [CompletionResultType]::ParameterName, 'Compile a parser in debug mode')
            [CompletionResult]::new('-D', '-D ', [CompletionResultType]::ParameterName, 'Produce the log.html file with debug graphs')
            [CompletionResult]::new('--debug-graph', '--debug-graph', [CompletionResultType]::ParameterName, 'Produce the log.html file with debug graphs')
            [CompletionResult]::new('--wasm', '--wasm', [CompletionResultType]::ParameterName, 'Compile parsers to wasm instead of native dynamic libraries')
            [CompletionResult]::new('--open-log', '--open-log', [CompletionResultType]::ParameterName, 'Open `log.html` in the default browser, if `--debug-graph` is supplied')
            [CompletionResult]::new('--show-fields', '--show-fields', [CompletionResultType]::ParameterName, 'Force showing fields in test diffs')
            [CompletionResult]::new('-r', '-r', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('--rebuild', '--rebuild', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('--overview-only', '--overview-only', [CompletionResultType]::ParameterName, 'Show only the pass-fail overview tree')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;fuzz' {
            [CompletionResult]::new('-s', '-s', [CompletionResultType]::ParameterName, 'List of test names to skip')
            [CompletionResult]::new('--skip', '--skip', [CompletionResultType]::ParameterName, 'List of test names to skip')
            [CompletionResult]::new('--subdir', '--subdir', [CompletionResultType]::ParameterName, 'Subdirectory to the language')
            [CompletionResult]::new('--edits', '--edits', [CompletionResultType]::ParameterName, 'Maximum number of edits to perform per fuzz test')
            [CompletionResult]::new('--iterations', '--iterations', [CompletionResultType]::ParameterName, 'Number of fuzzing iterations to run per test')
            [CompletionResult]::new('-i', '-i', [CompletionResultType]::ParameterName, 'Only fuzz corpus test cases whose name matches the given regex')
            [CompletionResult]::new('--include', '--include', [CompletionResultType]::ParameterName, 'Only fuzz corpus test cases whose name matches the given regex')
            [CompletionResult]::new('-e', '-e', [CompletionResultType]::ParameterName, 'Only fuzz corpus test cases whose name does not match the given regex')
            [CompletionResult]::new('--exclude', '--exclude', [CompletionResultType]::ParameterName, 'Only fuzz corpus test cases whose name does not match the given regex')
            [CompletionResult]::new('--log-graphs', '--log-graphs', [CompletionResultType]::ParameterName, 'Enable logging of graphs and input')
            [CompletionResult]::new('-l', '-l', [CompletionResultType]::ParameterName, 'Enable parser logging')
            [CompletionResult]::new('--log', '--log', [CompletionResultType]::ParameterName, 'Enable parser logging')
            [CompletionResult]::new('-r', '-r', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('--rebuild', '--rebuild', [CompletionResultType]::ParameterName, 'Force rebuild the parser')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;query' {
            [CompletionResult]::new('--paths', '--paths', [CompletionResultType]::ParameterName, 'The path to a file with paths to source file(s)')
            [CompletionResult]::new('--byte-range', '--byte-range', [CompletionResultType]::ParameterName, 'The range of byte offsets in which the query will be executed')
            [CompletionResult]::new('--row-range', '--row-range', [CompletionResultType]::ParameterName, 'The range of rows in which the query will be executed')
            [CompletionResult]::new('--scope', '--scope', [CompletionResultType]::ParameterName, 'Select a language by the scope instead of a file extension')
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('--time', '--time', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('-c', '-c', [CompletionResultType]::ParameterName, 'Order by captures instead of matches')
            [CompletionResult]::new('--captures', '--captures', [CompletionResultType]::ParameterName, 'Order by captures instead of matches')
            [CompletionResult]::new('--test', '--test', [CompletionResultType]::ParameterName, 'Whether to run query tests or not')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;highlight' {
            [CompletionResult]::new('--captures-path', '--captures-path', [CompletionResultType]::ParameterName, 'The path to a file with captures')
            [CompletionResult]::new('--query-paths', '--query-paths', [CompletionResultType]::ParameterName, 'The paths to files with queries')
            [CompletionResult]::new('--scope', '--scope', [CompletionResultType]::ParameterName, 'Select a language by the scope instead of a file extension')
            [CompletionResult]::new('--paths', '--paths', [CompletionResultType]::ParameterName, 'The path to a file with paths to source file(s)')
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-H', '-H ', [CompletionResultType]::ParameterName, 'Generate highlighting as an HTML document')
            [CompletionResult]::new('--html', '--html', [CompletionResultType]::ParameterName, 'Generate highlighting as an HTML document')
            [CompletionResult]::new('--check', '--check', [CompletionResultType]::ParameterName, 'Check that highlighting captures conform strictly to standards')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('--time', '--time', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;tags' {
            [CompletionResult]::new('--scope', '--scope', [CompletionResultType]::ParameterName, 'Select a language by the scope instead of a file extension')
            [CompletionResult]::new('--paths', '--paths', [CompletionResultType]::ParameterName, 'The path to a file with paths to source file(s)')
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('--time', '--time', [CompletionResultType]::ParameterName, 'Measure execution time')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Suppress main output')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;playground' {
            [CompletionResult]::new('--grammar-path', '--grammar-path', [CompletionResultType]::ParameterName, 'Path to the directory containing the grammar and wasm files')
            [CompletionResult]::new('-q', '-q', [CompletionResultType]::ParameterName, 'Don''t open in default browser')
            [CompletionResult]::new('--quiet', '--quiet', [CompletionResultType]::ParameterName, 'Don''t open in default browser')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;dump-languages' {
            [CompletionResult]::new('--config-path', '--config-path', [CompletionResultType]::ParameterName, 'The path to an alternative config.json file')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'tree-sitter;complete' {
            [CompletionResult]::new('-s', '-s', [CompletionResultType]::ParameterName, 'The shell to generate completions for')
            [CompletionResult]::new('--shell', '--shell', [CompletionResultType]::ParameterName, 'The shell to generate completions for')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
