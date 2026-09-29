# Shared by Fish's conf.d startup and dots init; guard is shell-local.
if status is-interactive; and not set -q _dots_fish_autopair_ready
    set -l dots_fish_root (path dirname (path dirname (path resolve (status filename))))
    source "$dots_fish_root/integrations/autopair.fish"
    set -g _dots_fish_autopair_ready 1
end
