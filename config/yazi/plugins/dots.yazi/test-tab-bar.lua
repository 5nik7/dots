-- Run from the plugin checkout with lua test-tab-bar.lua.
local bar = dofile("tab-bar.lua")
local family = "unix"
ya = { target_family = function() return family end }

-- ASCII truncation fixture. Native checks exercise Yazi's cell-width handling.
ui = {
  truncate = function(text, options)
    if #text <= options.max then return text end
    return text:sub(1, options.max - 1) .. "…"
  end,
  Constraint = { Length = function(n) return n end, Fill = function() return "fill" end },
}
local layout = {}
function layout:direction() return self end
function layout:constraints(rows) self.rows = rows; return self end
function layout:split() return self.rows end
ui.Layout = setmetatable({ VERTICAL = 1 }, { __call = function() return layout end })
local function widget(id)
  return { new = function(_, area) return { id = id, area = area } end }
end
Header, Tab, Status, Modal = widget("header"), widget("tab"), widget("status"), widget("modal")
Root = {}
rt = { term = { light = false } }
cx = { tabs = {} }

local function url(path)
  local name = path:match("([^/]+)$")
  local parent_path = path:match("^(.*)/[^/]+$")
  local parent = parent_path and url(parent_path ~= "" and parent_path or "/")
  return setmetatable({ name = name, parent = parent, spec = { is_regular = true } },
    { __tostring = function() return path end })
end
local function tab(path, custom)
  local cwd = url(path)
  return { current = { cwd = cwd }, name = custom or cwd.name or "/", pref = { name = custom or "" } }
end
local function labels(tabs, expected, mode, width)
  local actual = table.concat(bar.labels(tabs, mode, width or 20), "|")
  assert(actual == expected, ("expected %s, got %s"):format(expected, actual))
end

local a, b, c = tab("/project/src"), tab("/project/src"), tab("/project/docs")
labels({a, b}, "1|2", "auto")
labels({a, b, c}, "1 src|2 src|3 docs", "auto")
labels({c, a, b}, "1 docs|2 src|3 src", "auto")
labels({a, tab("/project/src", "review")}, "1 src|2 review", "auto")
labels({tab("/a", "review"), tab("/b", "review")}, "1 review|2 review", "auto")
labels({tab("/a", "review"), tab("/a", "review")}, "1|2", "auto")
labels({a, tab("/src"), tab("/home/src")}, "1 project/src|2 /src|3 home/src", "auto")
labels({tab("/a/x/src"), tab("/b/x/src"), tab("/b/y/src"), tab("/b/x/src")},
  "1 a/x/src|2 b/x/src|3 y/src|4 b/x/src", "auto")
labels({tab("/a/src", "src"), tab("/b/src", "src")}, "1 src|2 src", "auto")
labels({tab("/a/src"), tab("/b/src")}, "1 src|2 src", "name")
labels({a, c}, "1|2", "number")
labels({a, c}, "1|2", "auto", 0)
labels({a, c}, "1 …|2 …", "name", 3)
labels({tab("/a", "a\nb"), c}, "1 a b|2 docs", "auto")
labels({a, a}, "1 src|2 src", nil)
labels({a, a}, "1|2", nil, 0)
family = "windows"
labels({tab("/a/src"), tab("/b/src")}, "1 a\\src|2 b\\src", "auto")
family = "unix"
local many = {}
for i = 1, 100 do many[i] = a end
assert(bar.labels(many, "name", 3)[100] == "100")

local values = { hide_in_tmux = true, width = 20, labels = "auto" }
assert(not bar.update(values, false))
assert(not bar.update(values, { labels = "bad", width = 4097, hide_in_tmux = 1, from_dots_config = true }))
assert(bar.update(values, { hide_in_tmux = false, width = 0, labels = "number" }))
assert(not values.hide_in_tmux and values.width == 0 and values.labels == "number")
assert(not bar.update(values, { labels = "number", width = 1.5, only_with_multiple_tabs = "false" }))
assert(bar.update(values, { width = 4096, only_with_multiple_tabs = true }))

local saved_require, saved_getenv = require, os.getenv
require = function(name) assert(name == ".tab-bar"); return bar end
local function setup(tmux, options)
  local component = dofile("dotline.lua")
  os.getenv = function(key) assert(key == "TMUX"); return tmux end
  component:setup(options or {})
  os.getenv = function() error("environment read during redraw") end
  return component
end
local function rows(tabs, expected)
  cx.tabs, cx.active = tabs, tabs[1]
  local root = { _area = "screen" }
  Root.layout(root)
  Root.build(root)
  local sequence = {}
  for _, child in ipairs(root._children) do
    sequence[#sequence + 1] = child.id
    local correct_area = ({ tab = "fill", status = 1, header = 1, modal = "screen" })[child.id]
    assert(child.area == correct_area, child.id)
  end
  assert(#root._children == #root._chunks + 1)
  assert(table.concat(sequence, " ") == expected, table.concat(sequence, " "))
end
local policy = { hide_in_tmux = true, only_with_multiple_tabs = true, labels = "auto" }
for _, tmux in ipairs({ false, "", "private.sock,123,0" }) do
  local component = setup(tmux or nil, { tab_bar = policy })
  rows({a}, "tab status modal")
  local outside = not tmux or tmux == ""
  rows({a, b}, outside and "header tab status modal" or "tab status modal")
  rows({a}, "tab status modal")
  assert(component:set_tab_bar({ hide_in_tmux = false, only_with_multiple_tabs = false }))
  rows({a}, "header tab status modal")
end
setup("tmux", { component_positions = { "status", "tab", "header" }, tab_bar = policy })
rows({a, b}, "status tab modal")
setup(nil, { display_header_line = false, theme = { display_header_line = true }, tab_bar = policy })
rows({a, b}, "tab status modal")
setup("tmux")
rows({a}, "header tab status modal")
require, os.getenv = saved_require, saved_getenv
print("PASS tab labels, width, partial settings, raw tmux detection and live header geometry")

local json = dofile("json.lua")
local key = "apps.yazi.tab_bar"
local unix = { "dots", "config", "get", key, "--json" }
local function check_bridge(platform, checkout, reply, expected_argv, expect_change)
  local state, events, calls = { _id = "dots.tab-bar-config" }, {}, 0
  local options = { hide_in_tmux = true, width = 20 }
  local command = { NULL = "null", PIPED = "piped" }
  function command:arg(args) table.move(args, 1, #args, #self.argv + 1, self.argv); return self end
  function command:stdin(value) assert(value == self.NULL); return self end
  function command:stdout(value) assert(value == self.PIPED); return self end
  command.stderr = command.stdin
  setmetatable(command, { __call = function(self, program)
    return setmetatable({ argv = { program } }, { __index = self })
  end })
  local modules = {
    [".json"] = json,
    [".dotline"] = { set_tab_bar = function(_, values)
      assert(expect_change, "unexpected configuration update")
      return bar.update(options, values)
    end },
    [".process"] = { output = function(cmd, timeout, limit)
      assert(timeout == 5 and limit == 65536)
      assert(#cmd.argv == #expected_argv)
      for i, word in ipairs(expected_argv) do assert(cmd.argv[i] == word, cmd.argv[i]) end
      calls = calls + 1
      return reply
    end },
  }
  local env = setmetatable({
    Command = command, require = function(name) return assert(modules[name]) end,
    os = { getenv = function(k) assert(k == "DOTS" and platform == "windows"); return checkout end },
    ya = {
      sync = function(fn) return function(...) return fn(state, ...) end end,
      target_os = function() return platform end,
      emit = function(event, args)
        if event == "plugin" then assert(args[1] == "dots" and args[2] == "tab-bar-config") end
        events[#events + 1] = event
      end,
    },
  }, { __index = _G })
  local bridge = assert(loadfile("tab-bar-config.lua", "t", env))()
  bridge.read()
  assert(calls == 0)
  bridge.setup(state)
  bridge.setup(state)
  bridge.read()
  bridge.setup(state)
  bridge.read()
  assert(calls == 1)
  assert(table.concat(events, ",") == (expect_change and "plugin,app:resize" or "plugin"))
  assert(options.hide_in_tmux == (not expect_change) and options.width == (expect_change and 0 or 20))
end
local valid = json.encode({ schema = 1, key = key, value = { hide_in_tmux = false, width = 0 } })
check_bridge("windows", "C:/Dots Checkout", valid, {
  "powershell.exe", "-NoProfile", "-NonInteractive", "-File",
  "C:/Dots Checkout/bin/dots.ps1", "config", "get", key, "--json",
}, true)
check_bridge("windows", nil, valid, {
  "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
  "dots.ps1 config get apps.yazi.tab_bar --json; exit $LASTEXITCODE",
}, true)
check_bridge("linux", nil, valid, unix, true)
check_bridge("linux", nil, nil, unix, false)
check_bridge("linux", nil, "{bad", unix, false)
check_bridge("linux", nil, json.encode({ schema = 1, key = "other", value = {} }), unix, false)
print("PASS one-shot Dots lookup, Unix and Windows argv, false/zero overrides and response fallback")
