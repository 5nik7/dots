#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc

if [ -e /home/njen/.nix-profile/etc/profile.d/nix.sh ]; then . /home/njen/.nix-profile/etc/profile.d/nix.sh; fi # added by Nix installer
