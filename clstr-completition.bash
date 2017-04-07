#!/bin/bash

WDIR=${WDIR:-"$HOME/work"}

_clstr_screen() {
	COMPREPLY=()
	if [[ ${COMP_CWORD} == 1 ]] ; then
		cur="${COMP_WORDS[COMP_CWORD]}"
		d=$(ls -1 $WDIR | grep clstr | sed 's/clstr\-//')
		COMPREPLY=($(compgen -W "$d" -- $cur))
	fi
}

complete -F _clstr_screen clstr_screen
