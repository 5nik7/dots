# Fish may source this file through native conf.d and through the checkout entry.
status is-interactive; or return 0
set -q _dots_fish_usage_ready; and return 0

command -q usage; and usage g completion-init fish | source
set -g _dots_fish_usage_ready 1
