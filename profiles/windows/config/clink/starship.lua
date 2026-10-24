-- Preserve deliberate overrides; retire the former Dots-configured location.
local configured = os.getenv("STARSHIP_CONFIG")
local roots = {"C:/Users/njen/dots/configs"}
for _, name in ipairs({"DOTFILES", "DOTCONFIG"}) do
  local root = os.getenv(name)
  if root and root ~= "" then table.insert(roots, root) end
end
for _, entry in ipairs({
  {"DOTS", {"/config", "/configs"}},
  {"USERPROFILE", {"/dots/config", "/dots/configs", "/.dots/config", "/.dots/configs"}},
}) do
  local root = os.getenv(entry[1])
  if root and root ~= "" then
    for _, suffix in ipairs(entry[2]) do table.insert(roots, root .. suffix) end
  end
end
if configured then
  for _, root in ipairs(roots) do
    if root ~= "" and configured:gsub("\\", "/"):lower() ==
      (root:gsub("\\", "/"):gsub("/$", "") .. "/starship/starship.toml"):lower() then
      os.setenv("STARSHIP_CONFIG", "")
      break
    end
  end
end

os.setenv("STARSHIP_CACHE", "C:\\Users\\njen\\AppData\\Local\\Temp")

load(io.popen("starship init cmd"):read("*a"))()
