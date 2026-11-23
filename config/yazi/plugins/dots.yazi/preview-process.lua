--- @since 26.9.1
local M = { max_input=2*1024*1024, max_output=8*1024*1024, timeout=5 }
local function append(dst, src) for _,v in ipairs(src or {}) do dst[#dst+1]=v end end
function M.arguments(renderer, opts, width, height, path)
  local args={};append(args,(opts.args or {})[renderer])
  if renderer=="chafa" then
    append(args,{"--format","symbols","--symbols",opts.symbols,"--relative","off","--probe","off","--polite","on","--passthrough","none","--animate","off","--view-size",string.format("%dx%d",width,height)})
  elseif renderer=="leaf" then
    append(args,{"--inline","ansi:"..width})
  elseif renderer=="mdcat" then
    append(args,{"--ansi","--local","--no-pager","--image-protocol","none","--columns",tostring(width)})
  elseif renderer=="glow" then
    append(args,{"--width",tostring(width),"--pager=false"})
  elseif renderer=="rich" then
    append(args,{"--markdown","--force-terminal","--width",tostring(width)})
  elseif renderer=="bat" then
    append(args,{"--color=always","--paging=never","--style=plain","--language=markdown","--wrap=character","--terminal-width="..width})
  else error("unsupported preview command") end
  append(args,{"--",path});return args
end
function M.run(renderer, opts, width, height, path)
  local cmd=Command(renderer):arg(M.arguments(renderer,opts,width,height,path))
    :stdin(Command.NULL):stdout(Command.PIPED):stderr(Command.PIPED)
    :env("PAGER",""):env("BAT_PAGER",""):env("GLOW_PAGER","false"):env("GLOW_TUI","false")
    :env("CLICOLOR_FORCE","1"):env("FORCE_COLOR","1")
  return require(".process").output(cmd, M.timeout, M.max_output, "output exceeded 8 MiB")
end
function M.plain(path)
  local f=io.open(path,"rb");if not f then return nil,"could not read" end
  local text=f:read(M.max_input+1);f:close()
  if not text or #text>M.max_input then return nil,"input exceeded 2 MiB" end
  -- Treat source literally, including ESC; ui.Text must never parse source as ANSI.
  return text:gsub("\27","^["):gsub("\r\n","\n")
end
return M
