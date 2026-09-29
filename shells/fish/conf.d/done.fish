# Shared by Fish's conf.d startup and dots init; guard is shell-local.
if status is-interactive; and not set -q _dots_fish_done_ready
    set -l dots_fish_root (path dirname (path dirname (path resolve (status filename))))
    source "$dots_fish_root/integrations/done.fish"
    set -g _dots_fish_done_ready 1
end
