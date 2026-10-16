; Dots shell syntax colors. Empty secondary keeps nested syntax in this theme.
[base]
default          = {{ foreground }}
unknown-token    = {{ error }},bold
commandseparator = {{ muted }}
redirection      = {{ cyan }}
here-string-tri  = {{ cyan }}
here-string-text = {{ bright_green }}
here-string-var  = {{ cyan }}
exec-descriptor  = {{ orange }}
comment          = {{ muted }}
correct-subtle   = {{ cyan }}
incorrect-subtle = {{ error }}
subtle-separator = {{ muted }}
subtle-bg        = bg:{{ selection }}
secondary        =
recursive-base   = {{ foreground }}

[command-point]
reserved-word     = {{ magenta }}
subcommand        = {{ green }}
alias             = {{ green }}
suffix-alias      = {{ green }}
global-alias      = {{ green }}
builtin           = {{ green }}
function          = {{ green }}
command           = {{ green }}
precommand        = {{ magenta }}
hashed-command    = {{ green }}
single-sq-bracket = {{ magenta }}
double-sq-bracket = {{ magenta }}
double-paren      = {{ magenta }}

[paths]
path          = {{ foreground }}
pathseparator = {{ muted }}
path-to-dir   = {{ blue }},bold
globbing      = {{ cyan }}
globbing-ext  = {{ cyan }}

[brackets]
paired-bracket  = bg:{{ selection }}
bracket-level-1 = {{ green }}
bracket-level-2 = {{ yellow }}
bracket-level-3 = {{ cyan }}

[arguments]
single-hyphen-option   = {{ cyan }}
double-hyphen-option   = {{ cyan }}
back-quoted-argument   = {{ cyan }}
single-quoted-argument = {{ bright_green }}
double-quoted-argument = {{ bright_green }}
dollar-quoted-argument = {{ bright_green }}
optarg-string          = {{ bright_green }}
optarg-number          = {{ orange }}

[in-string]
back-dollar-quoted-argument           = {{ cyan }}
back-or-dollar-double-quoted-argument = {{ cyan }}

[other]
variable             = {{ foreground }}
assign               = {{ magenta }}
assign-array-bracket = {{ magenta }}
history-expansion    = {{ cyan }}

[math]
mathvar = {{ foreground }}
mathnum = {{ orange }}
matherr = {{ error }},bold

[for-loop]
forvar  = {{ foreground }}
fornum  = {{ orange }}
foroper = {{ magenta }}
forsep  = {{ muted }}

[case]
case-input       = {{ foreground }}
case-parentheses = {{ magenta }}
case-condition   = {{ cyan }}
