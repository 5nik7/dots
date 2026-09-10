package extension

import (
	"encoding/json"
	"strings"
	"testing"
)

func fixtureMetadata(route ...string) Metadata {
	return Metadata{1, route, "Fixture command", strings.Join(route, " ") + " [args]", []string{"dots " + strings.Join(route, " ")}, []string{"termux", "linux", "windows"}, false, []Output{{"text", 0}}, "read-only", []string{}, []string{}}
}
func encode(m Metadata) []byte {
	b, err := json.Marshal(m)
	if err != nil {
		panic(err)
	}
	return b
}
func TestStrictMetadata(t *testing.T) {
	good := string(encode(fixtureMetadata("fixture")))
	bad := []string{good + "{}", strings.Replace(good, `"hidden":false`, `"hidden":false,"hidden":true`, 1), strings.Replace(good, `"schema_version":0`, `"schema_version":0,"schema_version":1`, 1), strings.Replace(good, `"hidden":false,`, "", 1), strings.Replace(good, `"hidden":false`, `"Hidden":false`, 1), strings.Replace(good, `"hidden":false`, `"hidden":null`, 1), strings.Replace(good, `"aliases":[]`, `"aliases":["f"]`, 1), strings.Replace(good, `"capabilities":[]`, `"capabilities":["network"]`, 1), strings.Replace(good, "read-only", "external-side-effect", 1), strings.Replace(good, `"text"`, `"xml"`, 1), strings.Replace(good, `,"schema_version":0`, "", 1), strings.Replace(good, "Fixture command", `line\nline`, 1), strings.Replace(good, "Fixture command", `\u001b`, 1), strings.Replace(good, "Fixture command", `\ud800`, 1), strings.Replace(good, "Fixture command", string([]byte{255}), 1), strings.Repeat(" ", MaxMetadataBytes) + good, strings.Replace(good, `"aliases":[]`, `"aliases":`+strings.Repeat("[", 18)+strings.Repeat("]", 18), 1)}
	for i, s := range bad {
		if _, err := Parse([]byte(s), "dots-fixture"); err == nil {
			t.Fatalf("accepted case %d", i)
		}
	}
	if _, err := Parse([]byte(good), "dots-other"); err == nil {
		t.Fatal("route mismatch")
	}
	m, err := Parse([]byte(good), "dots-fixture")
	if err != nil {
		t.Fatal(err)
	}
	projection := m.Projection()
	projection.Route[0] = "changed"
	projection.Examples[0] = "changed"
	if m.Route[0] != "fixture" || m.Examples[0] == "changed" {
		t.Fatal("mutable projection")
	}
}
