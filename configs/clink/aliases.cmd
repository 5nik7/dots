@echo off
doskey c=cls
doskey q=exit
doskey l=eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time
doskey ll=eza -lA --git --git-repos --icons --group-directories-first --no-quotes
doskey ip=ipconfig $*
doskey hosts=code C:\Windows\System32\drivers\etc\hosts
doskey aliases=code C:\repos\dots\configs\clink\aliases.cmd