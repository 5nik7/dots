# Dots semantic theme, adapted from config/eza/themes/catppuccin-mocha-mauve.yml.
colourful: true

filekinds:
  normal: {foreground: "{{ foreground }}"}
  directory: {foreground: "{{ accent }}"}
  symlink: {foreground: "{{ blue }}"}
  pipe: {foreground: "{{ light_foreground }}"}
  block_device: {foreground: "{{ red }}"}
  char_device: {foreground: "{{ red }}"}
  socket: {foreground: "{{ light_foreground }}"}
  special: {foreground: "{{ accent }}"}
  executable: {foreground: "{{ green }}"}
  mount_point: {foreground: "{{ cyan }}"}

perms:
  user_read: {foreground: "{{ red }}", is_bold: true}
  user_write: {foreground: "{{ yellow }}", is_bold: true}
  user_execute_file: {foreground: "{{ green }}", is_bold: true}
  user_execute_other: {foreground: "{{ green }}", is_bold: true}
  group_read: {foreground: "{{ red }}"}
  group_write: {foreground: "{{ yellow }}"}
  group_execute: {foreground: "{{ green }}"}
  other_read: {foreground: "{{ red }}"}
  other_write: {foreground: "{{ yellow }}"}
  other_execute: {foreground: "{{ green }}"}
  special_user_file: {foreground: "{{ accent }}"}
  special_other: {foreground: "{{ muted }}"}
  attribute: {foreground: "{{ dark_foreground }}"}

size:
  major: {foreground: "{{ light_foreground }}"}
  minor: {foreground: "{{ bright_cyan }}"}
  number_byte: {foreground: "{{ light_foreground }}"}
  number_kilo: {foreground: "{{ light_foreground }}"}
  number_mega: {foreground: "{{ blue }}"}
  number_giga: {foreground: "{{ accent }}"}
  number_huge: {foreground: "{{ accent }}"}
  unit_byte: {foreground: "{{ light_foreground }}"}
  unit_kilo: {foreground: "{{ bright_cyan }}"}
  unit_mega: {foreground: "{{ accent }}"}
  unit_giga: {foreground: "{{ accent }}"}
  unit_huge: {foreground: "{{ cyan }}"}

users:
  user_you: {foreground: "{{ foreground }}"}
  user_root: {foreground: "{{ red }}"}
  user_other: {foreground: "{{ red }}"}
  group_yours: {foreground: "{{ light_foreground }}"}
  group_other: {foreground: "{{ dark_foreground }}"}
  group_root: {foreground: "{{ red }}"}

links:
  normal: {foreground: "{{ blue }}"}
  multi_link_file: {foreground: "{{ blue }}"}

git:
  new: {foreground: "{{ git_added_eza }}"}
  modified: {foreground: "{{ git_modified_eza }}"}
  deleted: {foreground: "{{ git_deleted_eza }}"}
  renamed: {foreground: "{{ git_renamed_eza }}"}
  typechange: {foreground: "{{ git_modified_eza }}"}
  ignored: {foreground: "{{ git_ignored_eza }}"}
  conflicted: {foreground: "{{ git_conflict_eza }}"}

git_repo:
  branch_main: {foreground: "{{ git_branch_eza }}"}
  branch_other: {foreground: "{{ git_branch_eza }}"}
  git_clean: {foreground: "{{ git_clean_eza }}"}
  git_dirty: {foreground: "{{ git_modified_eza }}"}

security_context:
  selinux:
    colon: {foreground: "{{ dark_foreground }}"}
    user: {foreground: "{{ muted }}"}
    role: {foreground: "{{ accent }}"}
    typ: {foreground: "{{ muted }}"}
    range: {foreground: "{{ accent }}"}

file_type:
  image: {foreground: "{{ yellow }}"}
  video: {foreground: "{{ red }}"}
  music: {foreground: "{{ green }}"}
  lossless: {foreground: "{{ cyan }}"}
  crypto: {foreground: "{{ muted }}"}
  document: {foreground: "{{ foreground }}"}
  compressed: {foreground: "{{ magenta }}"}
  temp: {foreground: "{{ red }}"}
  compiled: {foreground: "{{ bright_blue }}"}
  source: {foreground: "{{ blue }}"}

punctuation: {foreground: "{{ dark_foreground }}"}
date: {foreground: "{{ yellow }}"}
inode: {foreground: "{{ light_foreground }}"}
blocks: {foreground: "{{ dark_foreground }}"}
header: {foreground: "{{ foreground }}"}
octal: {foreground: "{{ cyan }}"}
flags: {foreground: "{{ accent }}"}

symlink_path: {foreground: "{{ bright_cyan }}"}
control_char: {foreground: "{{ bright_blue }}"}
broken_symlink: {foreground: "{{ red }}"}
broken_path_overlay: {foreground: "{{ muted }}"}

