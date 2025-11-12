#!/usr/bin/env bash

GIT_REMOTE=$(command git remote get-url origin 2>/dev/null)
if [[ -z "$GIT_REMOTE" ]]; then
  GIT_REMOTE=$(command git ls-remote --get-url 2>/dev/null)
fi
if [[ "$GIT_REMOTE" =~ "github" ]]; then
  # GIT_REMOTE_SYMBOL=""
  GIT_REMOTE_SYMBOL=""
elif [[ "$GIT_REMOTE" =~ "gitlab" ]]; then
  GIT_REMOTE_SYMBOL=""
elif [[ "$GIT_REMOTE" =~ "bitbucket" ]]; then
  GIT_REMOTE_SYMBOL=""
elif [[ -n "$GIT_REMOTE" ]]; then
  GIT_REMOTE_SYMBOL=""
else
  GIT_REMOTE_SYMBOL=""
fi
echo "$GIT_REMOTE_SYMBOL"
