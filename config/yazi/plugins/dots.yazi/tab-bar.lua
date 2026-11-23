--- @diagnostic disable: undefined-global

local M = {}
local modes = { auto = true, name = true, number = true }

-- A partial configuration may come from init.lua or from Dots after setup.
function M.update(options, values)
  if type(values) ~= "table" then return false end
  local changed = false
  for key, value in pairs(values) do
    local valid = ((key == "hide_in_tmux" or key == "only_with_multiple_tabs") and type(value) == "boolean")
      or (key == "labels" and modes[value] == true)
      or (key == "width" and type(value) == "number" and value >= 0 and value <= 4096 and value % 1 == 0)
    if valid and options[key] ~= value then
      options[key] = value
      changed = true
    end
  end
  return changed
end

-- Each distinct directory has one entry, even when several tabs visit it.
-- Grow only colliding automatic labels, one parent at a time. At the root,
-- the full URL also distinguishes otherwise identical paths on different hosts.
local function distinguish(directories)
  local changed
  repeat
    local counts = {}
    for _, dir in pairs(directories) do
      counts[dir.label] = (counts[dir.label] or 0) + 1
    end
    changed = false
    for path, dir in pairs(directories) do
      if counts[dir.label] > 1 and dir.label ~= path then
        local parent = dir.url.parent
        if parent and parent.name then
          dir.label = parent.name .. dir.separator .. dir.label
          dir.url = parent
        else
          dir.label = path
        end
        changed = true
      end
    end
  until not changed
end

local function auto_names(tabs)
  if #tabs < 2 then return {} end
  local names, directories, automatic = {}, {}, {}
  local windows = ya.target_family() == "windows"
  local first_path, all_same = nil, true
  for i = 1, #tabs do
    local tab = tabs[i]
    local url, name = tab.current.cwd, tab.name
    local path = tostring(url)
    first_path = first_path or path
    names[i] = name
    all_same = all_same and path == first_path and name == names[1]
    if tab.pref.name == "" then
      if not directories[path] then
        directories[path] = {
          label = name,
          url = url,
          separator = windows and url.spec.is_regular and "\\" or "/",
        }
      end
      automatic[i] = directories[path]
    end
  end
  if all_same then return {} end
  distinguish(directories)
  for i, dir in pairs(automatic) do names[i] = dir.label end
  return names
end

function M.labels(tabs, mode, width)
  local names = mode == "auto" and width > 2 and auto_names(tabs) or {}
  local labels = {}
  for i = 1, #tabs do
    local number = tostring(i)
    labels[i] = number
    if mode == nil and width > 2 then
      -- Preserve Dotline's existing tab_width behavior for standalone users.
      labels[i] = ui.truncate(number .. " " .. tabs[i].name, { max = width })
    elseif mode ~= "number" and width > #number + 1 then
      local name = mode == "name" and tabs[i].name or names[i]
      if name and name ~= "" then
        labels[i] = number .. " " .. ui.truncate(name:gsub("%c", " "), { max = width - #number - 1 })
      end
    end
  end
  return labels
end

return M
