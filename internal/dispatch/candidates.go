package dispatch

import "errors"

const MaxCommandRoots = 8
const MaxRouteDepth = 8
const MaxRouteSegment = 24

// ExternalSegment excludes hyphens so filename-to-route mapping is one-to-one.
func ExternalSegment(s string) bool {
	if len(s) == 0 || len(s) > MaxRouteSegment || s[0] < 'a' || s[0] > 'z' {
		return false
	}
	for _, c := range s {
		if !(c >= 'a' && c <= 'z' || c >= '0' && c <= '9') {
			return false
		}
	}
	return true
}

func Protected(first string) bool {
	switch first {
	case "help", "doctor", "commands", "completion", "version", "status", "spec", "plan", "apply", "undo", "history", "backup", "config", "bootstrap", "self":
		return true
	}
	return false
}

// Candidates is pure: no environment, filesystem or process operations.
func Candidates(args []string) ([][]string, error) {
	n := 0
	for n < len(args) && ExternalSegment(args[n]) {
		n++
	}
	if n > MaxRouteDepth {
		return nil, errors.New("external route exceeds matching limit; delimit arguments with --")
	}
	result := make([][]string, 0, n)
	for i := n; i > 0; i-- {
		result = append(result, args[:i])
	}
	return result, nil
}

func ExternalHelp(args []string) bool {
	for _, arg := range args {
		if arg == "--" {
			return false
		}
		if arg == "-h" || arg == "--help" {
			return true
		}
	}
	return false
}
