package dispatch

import (
	"reflect"
	"strings"
	"testing"
)

func TestExternalCandidates(t *testing.T) {
	got, err := Candidates([]string{"files", "list", "--", "literal"})
	if err != nil || !reflect.DeepEqual(got, [][]string{{"files", "list"}, {"files"}}) {
		t.Fatal(got, err)
	}
	for _, s := range []string{"", "-x", "files-list", "../x", "日本語", "A", strings.Repeat("a", 25)} {
		if ExternalSegment(s) {
			t.Fatalf("accepted %q", s)
		}
	}
	if _, err = Candidates(strings.Fields("a b c d e f g h i")); err == nil {
		t.Fatal("depth")
	}
	for _, args := range [][]string{{"files", "--", "--help"}, {"files", "value"}} {
		if ExternalHelp(args) {
			t.Fatal("literal help")
		}
	}
	if !ExternalHelp([]string{"files", "value", "--help"}) {
		t.Fatal("help not intercepted")
	}
	for _, s := range []string{"help", "doctor", "commands", "completion", "version", "status", "spec", "plan", "apply", "undo", "history", "backup", "config", "bootstrap", "self"} {
		if !Protected(s) {
			t.Fatal(s)
		}
	}
	if Protected("files") {
		t.Fatal("resource namespace reserved")
	}
}
