#!/bin/bash

src=https://github.com/neovim/neovim
dst=$HOME/source/neovim

if [[ -d ${dst} ]]; then
  echo 'Update neovim sources.'
  cd ${dst}
    git pull
else
  echo 'Clone neovim sources.'
  git clone $src $dst
fi

echo 'Build neovim.'
cd ${dst}
sudo make CMANE_BUILD=RelWithDebInfo install
cd $HOME
