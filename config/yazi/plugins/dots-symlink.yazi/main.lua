---@diagnostic disable: undefined-global

local context
local hooks = {}

local function width(text)
  return ui.Line(text):width()
end

local function clean(text)
  return tostring(text):gsub("%c", " ")
end

local function option(options, key, fallback)
  if options[key] ~= nil then
    return options[key]
  end
  return fallback
end

local function part(options, prefix, color, max_length, shorten, rtl)
  local theme = options.theme or {}
  local limit = option(options, prefix .. "_max_length", max_length)
  assert(
    type(limit) == "number" and limit >= 0 and limit < math.huge and limit % 1 == 0,
    "dots-symlink: " .. prefix .. "_max_length must be a non-negative integer (0 means unlimited)"
  )
  return {
    color = theme[prefix .. "_color"] or options[prefix .. "_color"] or color,
    max_length = limit,
    shorten = option(options, prefix .. "_shorten", shorten),
    rtl = option(options, prefix .. "_rtl", rtl),
  }
end

-- Yatline getters do not receive the line's available width. Measure a render
-- with an empty component (keeping its padding/separators), then render to fit.
local function hook(component)
  if component.redraw == hooks[component] then
    return
  end
  local redraw = component.redraw
  local wrapped = function(self, ...)
    local previous = context
    local frame = { measuring = true, count = 0 }
    context = frame
    local ok, result = pcall(redraw, self, ...)
    if ok and frame.count > 0 then
      local occupied = result[1]:max_width() + result[2]:width()
      frame.measuring = false
      frame.budget = math.floor(math.max(0, self._area.w - occupied) / frame.count)
      ok, result = pcall(redraw, self, ...)
    end
    context = previous
    if not ok then
      error(result, 0)
    end
    return result
  end
  hooks[component] = wrapped
  component.redraw = wrapped
end

-- Candidates drop whole leading directories, retaining the closest directories
-- that fit. Widths strictly decrease so even tiny budgets always terminate.
local function candidates(text, separator, directory)
  local result = { text }
  local function add(value)
    if width(value) < width(result[#result]) then
      result[#result + 1] = value
    end
  end
  local chunks = {}
  for chunk in text:gmatch(separator == "\\" and "[^\\]+" or "[^/]+") do
    chunks[#chunks + 1] = chunk
  end
  for start = 1, #chunks do
    local suffix = table.concat(chunks, separator, start)
    add(".." .. separator .. suffix .. (directory and separator or ""))
  end
  if directory then
    add(".." .. separator)
    add("")
  end
  return result
end

local function item(text, config, variants)
  local values = variants or { text }
  local index = 1
  if config.shorten and config.max_length > 0 then
    while index < #values and width(values[index]) > config.max_length do
      -- Keep the omission marker until the actual window budget requires hiding it.
      if values[index + 1] == "" then
        break
      end
      index = index + 1
    end
    text = values[index]
    if width(text) > config.max_length then
      text = ui.truncate(text, { max = config.max_length, rtl = config.rtl })
    end
  end
  return { text = text, config = config, values = values, index = index }
end

local function next_candidate(value)
  local index = value.index + 1
  while index <= #value.values and width(value.values[index]) >= width(value.text) do
    index = index + 1
  end
  return index <= #value.values and index or nil
end

local function fit(parts, budget)
  local function total()
    local sum = 0
    for _, value in ipairs(parts) do
      sum = sum + width(value.text)
    end
    return sum
  end

  -- Reduce directory context before touching filenames or the arrow.
  while total() > budget do
    local selected, next_index
    for _, value in ipairs(parts) do
      local index = next_candidate(value)
      if index and (not selected or width(value.text) > width(selected.text)) then
        selected, next_index = value, index
      end
    end
    if not selected then
      break
    end
    selected.index = next_index
    selected.text = selected.values[next_index]
  end

  -- Extremely narrow windows may also need shorter filenames. Reduce the
  -- widest text first, preserving the arrow until all other text is exhausted.
  while total() > budget do
    local selected
    for _, value in ipairs(parts) do
      if not value.arrow and width(value.text) > 0 and (not selected or width(value.text) > width(selected.text)) then
        selected = value
      end
    end
    if not selected then
      for _, value in ipairs(parts) do
        if width(value.text) > 0 then
          selected = value
          break
        end
      end
    end
    if not selected then
      break
    end
    local current = width(selected.text)
    local target = math.max(0, current - math.min(total() - budget, math.max(1, math.ceil(current / 2))))
    selected.text = target == 0 and "" or ui.truncate(selected.text, { max = target, rtl = selected.config.rtl })
  end
end

return {
  setup = function(_, options)
    options = options or {}
    local theme = options.theme or {}
    local auto_fit = options.auto_fit ~= false
    local arrow = clean(options.arrow or "  ")
    local arrow_config = { color = theme.arrow_color or options.arrow_color or "darkgray", rtl = false }
    local path = part(options, "path", "blue", 0, true, true)
    local name = part(options, "name", "white", 0, options.shorten ~= false, false)
    local link = part(options, "link", "cyan", options.max_length or 0, options.shorten ~= false, options.rtl ~= false)

    function Yatline.coloreds.get:symlink()
      if auto_fit and context and context.measuring then
        context.count = context.count + 1
        return { { "", path.color } }
      end
      if auto_fit and context and context.budget == 0 then
        return nil
      end

      local current = cx.active.current
      local cwd = clean(ya.readable_path(tostring(current.cwd)))
      local separator = ya.target_family() == "windows" and current.cwd.spec.is_regular and "\\" or "/"
      local hovered = current.hovered
      if hovered and cwd:sub(-1) ~= separator then
        cwd = cwd .. separator
      end
      local paths = candidates(cwd, separator, hovered ~= nil)
      local parts = { item(cwd, path, paths) }
      if hovered then
        parts[#parts + 1] = item(clean(hovered.name), name)
        if hovered.link_to then
          parts[#parts + 1] = { text = arrow, config = arrow_config, values = { arrow }, index = 1, arrow = true }
          local target = clean(hovered.link_to)
          parts[#parts + 1] = item(target, link, candidates(target, separator, false))
        end
      end
      if auto_fit and context then
        fit(parts, context.budget)
      end
      local spans = {}
      for _, value in ipairs(parts) do
        spans[#spans + 1] = { value.text, value.config.color }
      end
      return spans
    end

    if auto_fit then
      hook(Header)
      hook(Status)
    end
  end,
}
