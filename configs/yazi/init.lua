require("full-border"):setup({
  -- Available values: ui.Border.PLAIN, ui.Border.ROUNDED
  type = ui.Border.PLAIN,
  -- type = ui.Border.DOUBLE,
})

require("git"):setup({
  order = 1500,
})

th.git = th.git or {}
th.git.modified = ui.Style():fg("yellow")
th.git.deleted = ui.Style():fg("red"):bold()

require("folder-rules"):setup()

Status:children_add(function(self)
  local arrow = " -> "
  local h = self._current.hovered
  if h and h.link_to then
    return ui.Line({
      ui.Span(tostring(arrow)):fg("darkgray"),
      ui.Span(tostring(h.link_to)):fg("cyan"),
    })
  else
    return ""
  end
end, 3300, Status.LEFT)
