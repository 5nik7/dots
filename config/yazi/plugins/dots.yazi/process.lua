--- @since 26.9.1
-- Collect stdout from a piped command within one deadline, including process exit.
local function output(command, timeout, limit, limit_message)
  local child = command:spawn()
  if not child then return nil, "could not start" end
  local deadline = ya.time() + timeout
  local chunks, size = {}, 0
  local function stop(reason)
    child:start_kill()
    return nil, reason
  end
  while true do
    local remaining = deadline - ya.time()
    if remaining <= 0 then return stop("timed out") end
    local line, event = child:read_line_with({ timeout = math.max(1, math.floor(remaining * 1000)) })
    if event == 3 then return stop("timed out") end
    if event == 2 then break end
    size = size + #(line or "")
    if size > limit then return stop(limit_message or "output exceeded limit") end
    if event == 0 then chunks[#chunks + 1] = line end
  end
  -- A child can close its streams and continue running.
  while ya.time() < deadline do
    local status, err = child:try_wait()
    if err then return stop("could not wait") end
    if status then
      if not status.success then return nil, "exited unsuccessfully" end
      return table.concat(chunks)
    end
    ya.sleep(0.01)
  end
  return stop("timed out")
end

return { output = output }
