#!/usr/bin/env bash

GIT_REMOTE=$(command git remote get-url origin 2> /dev/null)
if [[ -z "$GIT_REMOTE" ]]; then
GIT_REMOTE=$(command git ls-remote --get-url 2> /dev/null)
fi
GIT_REMOTE_URL=$(echo $GIT_REMOTE | sed -E 's/^https?:\\/\\/(.+@)?//; s/\\.git$//;  s/\\.git$//; s/.+@(.+):([[:digit:]]+)\\/(.+)$/\\1\\/\\3/; s/.+@(.+):(.+)$/\\1\\/\\2/; s/\\/$//')

REPO_NAME=$(echo $GIT_REMOTE_URL | sed -E 's/.+\\/([^\\/]+)$/\\1/')

echo "$REPO_NAME"
