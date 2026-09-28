-- Run: lua test-symlink.lua. Supply test_plugin and ui to use native Yazi text APIs.
if not ui then
  local function cells(text)
    local n = 0
    for _, c in utf8.codes(text) do n = n + ((c >= 0x3000 and c <= 0x9fff) and 2 or (c == 0x301 and 0 or 1)) end
    return n
  end
  ui = {
    Line = function(s) return { width = function() return cells(s) end } end,
    Text = function(lines) return { max_width = function() return lines[1]:width() end } end,
    truncate = function(s, opts)
      if cells(s) <= opts.max then return s end
      if opts.max == 0 then return "" end
      local chars, out = {}, ""
      for _, c in utf8.codes(s) do chars[#chars + 1] = utf8.char(c) end
      while #chars > 0 do
        local c = table.remove(chars, opts.rtl and #chars or 1)
        if cells(out .. c) > opts.max - 1 then break end
        out = opts.rtl and c .. out or out .. c
      end
      return opts.rtl and "…" .. out or out .. "…"
    end,
  }
end
local plugin = test_plugin or dofile("symlink.lua")
Dotline = { coloreds = { get = {} } }
local family = "unix"
ya = { readable_path = function(s) return s end, target_family = function() return family end }
cx = { active = { current = {} } }
local spans, rendered, renders
local fail = false
local function redraw(self)
  renders = (renders or 0) + 1
  if fail then error("injected redraw failure") end
  spans = Dotline.coloreds.get:symlink()
  local texts = {}
  for _, span in ipairs(spans or {}) do texts[#texts + 1] = span[1] end
  rendered = table.concat(texts)
  local left = ui.Text({ ui.Line("tabs: " .. (spans and "[" .. rendered .. "]" or "")) })
  if ui.Rect then left:area(ui.Rect { w = self._area.w, h = 1 }) end
  return { left, ui.Line(" right ") }
end
Header = { redraw = redraw }
Status = { redraw = redraw }
local function cwd(text)
  cx.active.current.cwd = setmetatable({ spec = { is_regular = true } }, { __tostring = function() return text end })
end
local function render(columns, status)
  renders = 0
  local result = (status and Status or Header).redraw({ _area = { w = columns } })
  if columns >= 13 then assert(result[1]:max_width() + result[2]:width() <= columns, rendered) end
  return rendered
end
plugin:setup({ arrow = " -> " })
cwd("/very/long/root/dir")
cx.active.current.hovered = { name = "hovered_name", link_to = "/another/long/root/dir/link" }
assert(render(200) == "/very/long/root/dir/hovered_name -> /another/long/root/dir/link")
assert(renders == 2)
local found = false
for columns = 0, 200 do
  if render(columns) == "../dir/hovered_name -> ../dir/link" then found = true end
end
assert(found, "expected directory-preserving layout")
assert(render(200) == "/very/long/root/dir/hovered_name -> /another/long/root/dir/link")
assert(render(55, true):find("hovered_name", 1, true))
assert(spans[1][2] == "blue" and spans[2][2] == "white" and spans[3][2] == "darkgray" and spans[4][2] == "cyan")
plugin:setup({ arrow = " -> " })
render(100)
assert(renders == 2, "setup must not multiply render wrappers")
cwd("/")
cx.active.current.hovered = { name = "file" }
assert(render(100) == "/file")
cwd("/tmp/")
assert(render(100) == "/tmp/file")
cx.active.current.hovered = nil
assert(render(100) == "/tmp/")
family = "windows"
cwd("C:\\long\\dir")
cx.active.current.hovered = { name = "file", link_to = "C:\\other\\dir\\link" }
for columns = 0, 100 do render(columns) end
assert(render(100) == "C:\\long\\dir\\file -> C:\\other\\dir\\link")
family = "unix"
cwd("/路径/文件夹")
cx.active.current.hovered = { name = "é\nfile", link_to = "/路径/目录/链接" }
for columns = 0, 100 do render(columns) end
assert(render(100) == "/路径/文件夹/é file -> /路径/目录/链接")
fail = true
assert(not pcall(render, 50))
fail = false
assert(Dotline.coloreds.get:symlink()[1][1] ~= "")
plugin:setup({ auto_fit = false, path_max_length = 7, path_shorten = false, link_max_length = 7, arrow = " -> " })
cwd("/long/root/dir")
cx.active.current.hovered = { name = "file", link_to = "/long/root/link" }
local values = Dotline.coloreds.get:symlink()
assert(values[1][1] == "/long/root/dir/")
assert(values[4][1] == "../link")
for _, prefix in ipairs({ "path", "name", "link" }) do
  for _, value in ipairs({ -1, 1.5, "40", math.huge }) do
    assert(not pcall(plugin.setup, plugin, { [prefix .. "_max_length"] = value }))
  end
end
print("dots-symlink: responsive layout checks passed")
