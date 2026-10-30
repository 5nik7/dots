# Shared semantic aliases for repository utility scripts. No operation logic.
source "${BASH_SOURCE[0]%/*}/ui.bash"
dots::style
c_reset=$DOTS_UI_RESET rst=$DOTS_UI_RESET
bold=$DOTS_UI_BOLD dim=$DOTS_UI_DIM italic='' underline='' rev=''
if [[ $DOTS_UI_RESET ]]; then italic=$'\e[3m'; underline=$'\e[4m'; rev=$'\e[7m'; fi
fg_black=$DOTS_UI_DIM fg_red=$DOTS_UI_RED fg_green=$DOTS_UI_GREEN
fg_yellow=$DOTS_UI_YELLOW fg_blue=$DOTS_UI_BLUE fg_darkblue=$DOTS_UI_BLUE
fg_magenta=$DOTS_UI_MAGENTA fg_cyan=$DOTS_UI_CYAN fg_white=''
black=$fg_black red=$fg_red green=$fg_green yellow=$fg_yellow blue=$fg_blue
magenta=$fg_magenta cyan=$fg_cyan white=$fg_white
BOLD=$bold UNDERLINE=$underline ITALIC=$italic DIM=$dim INVERT=$rev
BLINK='' INVIS='' GREY=$DOTS_UI_DIM BLACK=$black RED=$red GREEN=$green
YELLOW=$yellow BLUE=$blue DARKBLUE=$blue MAGENTA=$magenta CYAN=$cyan
errico=$DOTS_UI_ERROR warnico=$DOTS_UI_WARN errcolor=$red warncolor=$yellow
trashcolor=$green dircolor=$blue arrowcolor=$DOTS_UI_DIM
trashico='delete' arrowico='<-' arrowico_l='<-' arrowico_r='->'
if [[ $DOTS_UI_INFO != '[i]' ]]; then dots::icon navigation.delete '󰆴'; trashico=$REPLY; fi
