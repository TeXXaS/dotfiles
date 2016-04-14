export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# nodejs
export PATH=$PATH:/c/tools/nodejs/

# bash history
# append instead rewrite  
shopt -s histappend
# sizes
export HISTFILESIZE=1000000
export HISTSIZE=1000000
# ignore empty, duplicates
export HISTCONTROL=ignoreboth
# store immediately
export PROMPT_COMMAND='history -a'

# Add bash colors.
if [ -f ~/.bashrc.d/bash_colors ]; then
    source ~/.bashrc.d/bash_colors
fi

# Add bash aliases.
if [ -f ~/.bashrc.d/bash_aliases ]; then
    source ~/.bashrc.d/bash_aliases
fi