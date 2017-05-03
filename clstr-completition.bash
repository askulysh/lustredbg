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

_choose_vmcore() {
	COMPREPLY=()
	if [[ ${COMP_CWORD} == 1 ]] ; then
		cur="${COMP_WORDS[COMP_CWORD]}"
		f=$(ls | grep -E "^c.+cdump$|^vmcore$")
		[ -z "$f" ] &&
			f=$(ls |grep -v -E "^st_|^log.dk_|^analysis_|^dmesg_")
		COMPREPLY=($(compgen -W "$f" -- $cur))
	fi

}

complete -F _clstr_screen clstr_screen
complete -F _choose_vmcore crash_start
complete -F _choose_vmcore crash_mk
complete -F _choose_vmcore log_extr
complete -F _choose_vmcore parse_vmcore
