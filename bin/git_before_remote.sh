#!/usr/bin/env bash

GIT_BEFORE_REPO=$(command dirname $(git rev-parse --show-toplevel))
if [[ "$GIT_BEFORE_REPO" =~ "/mnt/c/Users/$USERNAME" ]]; then
  GIT_BEFORE_REPO=$(echo "$GIT_BEFORE_REPO" | sed "s|^/mnt/c/Users/$USERNAME|~|")
elif [[ "$GIT_BEFORE_REPO" =~ "C:/Users/$USERNAME" ]]; then
  GIT_BEFORE_REPO=$(echo "$GIT_BEFORE_REPO" | sed "s|^C:/Users/$USERNAME|~|")
else
  GIT_BEFORE_REPO=$(echo "$GIT_BEFORE_REPO" | sed "s|^$HOME|~|")
fi

echo "$GIT_BEFORE_REPO/"
