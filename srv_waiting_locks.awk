#!/usr/bin/gawk -f

BEGIN {
	st=0
}

/ldlm_completion_ast at/ {
	st=1
#	print $0
}

/[048c]0:ldlm_locks/ {
	if (st == 1) {
#		print $0
		print "ldlm_lock.l_resource,l_req_mode,l_last_activity 0x" substr($2, 2, 16)
		st=0
	}
}

END {
	print "quit"
}
