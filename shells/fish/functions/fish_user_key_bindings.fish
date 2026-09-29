function fish_user_key_bindings
  command -q fzf; and fzf --fish | source
end
