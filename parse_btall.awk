#!/bin/awk -f

BEGIN {
	prog=""
	n_stack = 0
}

/PID/ {
	if (prog != "") {
		split(prog, arr, " ")
		stack_pids[cur_stack] = stack_pids[cur_stack] " " arr[2] " " arr[8]
	}
	prog=$0
	cur_stack = ""
}

$1 ~/#[0-9]+/ {cur_stack = cur_stack " " $3}

END {
	for (s in stack_pids) {
		ss = s
		gsub(" ", "\n", ss)
		print "Stack : " ss
		print "Progs: " stack_pids[s]
		print "\n"
	}
}
