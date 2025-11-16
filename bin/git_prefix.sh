#!/usr/bin/env bash

GIT_PREFIX=$(command git rev-parse --show-prefix | sed 's:/*$::')
echo "$GIT_PREFIX"
