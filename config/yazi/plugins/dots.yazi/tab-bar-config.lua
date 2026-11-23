--- @since 26.9.1
-- Only Dots-managed configurations opt into a single profile read at startup.
local key = "apps.yazi.tab_bar"
local claim_read = ya.sync(function(state)
  if not state.pending then return false end
  state.pending = false
  return true
end)
local apply = ya.sync(function(_, options)
  if require(".dotline"):set_tab_bar(options) then ya.emit("app:resize", {}) end
end)

local function setup(state)
  if state.requested then return end
  state.requested, state.pending = true, true
  ya.emit("plugin", { state._id:match("^[^.]+"), "tab-bar-config" })
end

local function read()
  if not claim_read() then return end
  local command
  if ya.target_os() == "windows" then
    local shell = Command("powershell.exe"):arg({ "-NoProfile", "-NonInteractive" })
    local checkout = os.getenv("DOTS")
    if checkout and checkout ~= "" then
      command = shell:arg({ "-File", checkout .. "/bin/dots.ps1", "config", "get", key, "--json" })
    else
      command = shell:arg({ "-Command", "dots.ps1 config get apps.yazi.tab_bar --json; exit $LASTEXITCODE" })
    end
  else
    command = Command("dots"):arg({ "config", "get", key, "--json" })
  end
  command:stdin(Command.NULL):stdout(Command.PIPED):stderr(Command.NULL)
  local raw = require(".process").output(command, 5, 65536)
  if not raw then return end
  local ok, result = pcall(require(".json").decode, raw)
  if ok and type(result) == "table" and result.schema == 1
      and result.key == key and type(result.value) == "table" then
    apply(result.value)
  end
end

return { setup = setup, read = read }
