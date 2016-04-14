:colorscheme pyte

execute pathogen#infect()
filetype plugin indent on

syntax on
set history=100
set visualbell

set hlsearch
set smartcase
set ignorecase
set incsearch

if has("gui_running") == 0
    set shell=/bin/bash
endif
