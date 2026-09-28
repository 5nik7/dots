---@diagnostic disable: undefined-global

local save = ya.sync(function(this, cwd, request, name)
  if request ~= this.request or cx.active.current.cwd ~= Url(cwd) then
    return
  end

  this.cwd = cwd
  this.name = name
  ui.render()
end)

return {
  setup = function(this, options)
    options = options or {}
    local theme = options.theme or options
    local color = theme.repo_color or "blue"
    local prefix = options.repo_prefix or ""
    local symbol = options.repo_symbol or ""

    function Yatline.coloreds.get:repo_name()
      if not this.name or this.cwd ~= tostring(cx.active.current.cwd) then
        return nil
      end

      return { { prefix .. symbol .. this.name, color } }
    end

    local function refresh()
      this.request = (this.request or 0) + 1
      this.cwd = nil
      this.name = nil
      ui.render()

      local cwd = cx.active.current.cwd
      if not cwd.spec.is_regular then
        return
      end

      ya.emit("plugin", {
        this._id,
        ya.quote(tostring(cwd), true) .. " " .. tostring(this.request),
      })
    end

    for _, event in ipairs({ "cd", "tab", "rename", "bulk", "move", "trash", "delete" }) do
      ps.sub(event, refresh)
    end
  end,

  entry = function(_, job)
    local args = job.args or job
    local cwd, request = args[1], tonumber(args[2])
    if not cwd or not request then
      return
    end

    -- Resolve the nearest working tree without scanning files or reading remotes.
    local output = Command("git")
      :arg({ "rev-parse", "--show-toplevel" })
      :cwd(cwd)
      :stdout(Command.PIPED)
      :stderr(Command.NULL)
      :output()

    local name
    if output and output.status.success then
      local root = output.stdout:gsub("\r?\n$", "")
      if root ~= "" then
        name = Url(root).name
        if name then
          -- A filename may contain control characters; keep the status on one line.
          name = name:gsub("%c", " ")
        end
      end
    end

    save(cwd, request, name)
  end,
}
