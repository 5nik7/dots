# Generated Dots colors. Edit the template or shared color roles, not this file.
# Git foreground roles honor configured overrides; attributes are explicit here.
[color "branch"]
  current = "{{ git_branch }} bold"
  local = "{{ git_repo }}"
  remote = "{{ cyan }}"
  upstream = "{{ accent }}"
[color "diff"]
  meta = "{{ muted }} bold"
  frag = "{{ accent }} bold"
  old = "{{ git_deleted_delta }}"
  new = "{{ git_added_delta }}"
  commit = "{{ accent }} bold"
  whitespace = "{{ error }} reverse"
  oldMoved = "{{ magenta }} bold"
  newMoved = "{{ cyan }} bold"
  oldMovedAlternative = "{{ blue }} bold"
  newMovedAlternative = "{{ yellow }} bold"
[color "status"]
  header = "{{ muted }}"
  added = "{{ git_staged }} bold"
  changed = "{{ git_modified }} bold"
  untracked = "{{ git_untracked }} bold"
  nobranch = "{{ git_detached }}"
  unmerged = "{{ git_conflict }} bold"
  branch = "{{ git_branch }}"
  localBranch = "{{ git_branch }}"
  remoteBranch = "{{ cyan }}"
[color "decorate"]
  HEAD = "{{ accent }} bold"
  branch = "{{ git_branch }}"
  remoteBranch = "{{ cyan }}"
  tag = "{{ yellow }} bold"
  stash = "{{ muted }}"
[delta]
  features = dots
[delta "dots"]
  # Adapted from the local gitppuccin reference using shared semantic colors.
  {{ mode }} = true
  blame-palette = "{{ background }} {{ dark_background }} {{ darker_background }} {{ lighter_background }} {{ selection_background }}"
  commit-decoration-style = "{{ dark_foreground }} bold box ul"
  file-decoration-style = "{{ dark_foreground }}"
  file-style = "{{ foreground }}"
  hunk-header-decoration-style = "{{ dark_foreground }} box ul"
  hunk-header-file-style = bold
  hunk-header-line-number-style = "{{ light_foreground }} bold"
  hunk-header-style = file line-number syntax
  line-numbers-left-style = "{{ dark_foreground }}"
  line-numbers-right-style = "{{ dark_foreground }}"
  line-numbers-zero-style = "{{ dark_foreground }}"
  line-numbers-minus-style = "{{ git_deleted_delta }} bold"
  line-numbers-plus-style = "{{ git_added_delta }} bold"
  minus-style = "syntax {{ git_deleted_blend_10 }}"
  minus-emph-style = "bold syntax {{ git_deleted_blend_25 }}"
  plus-style = "syntax {{ git_added_blend_10 }}"
  plus-emph-style = "bold syntax {{ git_added_blend_25 }}"
  map-styles = "bold {{ magenta }} => syntax {{ magenta_blend_25 }}, bold {{ blue }} => syntax {{ blue_blend_25 }}, bold {{ cyan }} => syntax {{ cyan_blend_25 }}, bold {{ yellow }} => syntax {{ yellow_blend_25 }}"
