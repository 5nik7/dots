# Shared normalized record; the geocoder never replaces the input coordinates.
def finite: type == "number" and isfinite;
def text: if type == "string" and length > 0 and length <= 8192 then . else null end;
def coordinate:
  type == "object" and (.latitude | finite) and (.longitude | finite)
  and .latitude >= -90 and .latitude <= 90
  and .longitude >= -180 and .longitude <= 180;
def blank:
  {version:1, latitude:null, longitude:null, accuracy_m:null,
   city:null, state:null, state_code:null, postcode:null, county:null,
   country:null, country_code:null, street:null, house_number:null, address:null,
   source:$source, provider:null, age_seconds:null, cached:false,
   address_cached:false, stale:false, attribution:null};
if length == 1 then .[0] else error("expected one object") end |
if $action == "fix" then
  if coordinate and (has("API_ERROR") | not) then
    . as $raw | blank + {
      latitude:$raw.latitude, longitude:$raw.longitude,
      accuracy_m:($raw.accuracy | if finite and . >= 0 then . else null end),
      provider:($raw.provider | text),
      age_seconds:($raw.elapsedMs | if finite and . >= 0 then ./1000 else null end)
    }
  else error("invalid location") end
elif $action == "address" then
  if type != "object" or has("error") or (.address | type) != "object"
     or (.display_name | text) == null then error("address unavailable")
  else
    . as $raw | .address as $a | {
      city:([$a.city,$a.town,$a.village,$a.municipality,$a.hamlet] | map(text) | map(select(. != null)) | first // null),
      state:($a.state | text), state_code:($a["ISO3166-2-lvl4"] | text),
      postcode:($a.postcode | text), county:($a.county | text),
      country:($a.country | text), country_code:($a.country_code | text | if . then ascii_upcase else null end),
      street:([$a.road,$a.pedestrian,$a.footway,$a.path] | map(text) | map(select(. != null)) | first // null),
      house_number:($a.house_number | text), address:$raw.display_name,
      attribution:($raw.licence | text // "© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright")
    }
  end
else error("invalid action") end
