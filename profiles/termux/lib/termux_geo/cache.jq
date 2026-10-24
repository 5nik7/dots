# Cache validation and reads shared by the warm path and the locked slow path.
def finite_number: type == "number" and isfinite;
def valid_fix:
  .version == 1 and (.latitude|finite_number) and (.longitude|finite_number)
  and .latitude >= -90 and .latitude <= 90 and .longitude >= -180 and .longitude <= 180
  and (.age_seconds == null or (.age_seconds|finite_number) and .age_seconds >= 0);
def valid_address:
  type == "object" and (.address|type) == "string"
  and ((keys - ["city","state","state_code","postcode","county","country","country_code",
    "street","house_number","address","attribution"])|length) == 0
  and all(.[]; . == null or type == "string");
def valid_state:
  .version == 1 and (.devices|type) == "object" and (.addresses|type) == "array"
  and (.addresses|length) <= 32 and (.rate|type) == "object"
  and ((.devices|keys)-["gps","network","passive"]|length) == 0
  and all(.devices[]; type == "object" and (.data|valid_fix))
  and all(.addresses[]; type == "object" and (.key|type) == "string" and (.at|finite_number) and (.data|valid_address));
def cached_fix(provider; boot; now; wall; max_age; allow_stale):
  .devices[provider] | select(type == "object") | . as $entry |
  .data |
  .age_seconds = (if boot != "" and $entry.boot == boot and ($entry.at|type) == "number" and now >= $entry.at
    and ($entry.wall|type) == "number" and wall >= $entry.wall and (.age_seconds|type) == "number"
    then .age_seconds + ([now-$entry.at,wall-$entry.wall]|max) else null end) |
  .stale = (.age_seconds == null or .age_seconds > max_age or max_age == 0) |
  select(.stale == false or allow_stale == 1) | .cached = true;
def cached_address(key; wall):
  first(.addresses[] | select(.key == key and .at <= wall and wall-.at < 86400) | .data);
def render_pieces(pieces):
  . + {coordinates:([.latitude,.longitude]|map(tostring)|join(","))} as $data |
  [pieces[] | if startswith("L") then .[1:] else .[1:] as $f |
    if $data[$f] == null then error("unavailable field") else ($data[$f]|tostring) end end] | join("");
