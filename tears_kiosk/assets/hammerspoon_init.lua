hs.autoLaunch(true)

EDGE_BLOCKER_ENABLED = true
EDGE_BLOCKER_DEADZONE_TOP = 12
EDGE_BLOCKER_DEADZONE_BOTTOM = 16
EDGE_BLOCKER_TOGGLE_MODS = {"cmd", "alt", "ctrl"}
EDGE_BLOCKER_TOGGLE_KEY = "k"

function edgeBlockerToggle()
  EDGE_BLOCKER_ENABLED = not EDGE_BLOCKER_ENABLED
  hs.alert.show("Edge blocker: " .. (EDGE_BLOCKER_ENABLED and "ON" or "OFF"))
end

hs.hotkey.bind(EDGE_BLOCKER_TOGGLE_MODS, EDGE_BLOCKER_TOGGLE_KEY, edgeBlockerToggle)

function startEdgeBlocker()
  if EDGE_BLOCKER_TAP then
    EDGE_BLOCKER_TAP:stop()
    EDGE_BLOCKER_TAP = nil
  end

  EDGE_BLOCKER_TAP = hs.eventtap.new({
    hs.eventtap.event.types.mouseMoved,
    hs.eventtap.event.types.leftMouseDragged,
    hs.eventtap.event.types.rightMouseDragged,
    hs.eventtap.event.types.otherMouseDragged
  }, function(event)
    if not EDGE_BLOCKER_ENABLED then
      return false
    end

    local p = event:location()
    local s = hs.mouse.getCurrentScreen()
    if not s then
      return false
    end

    local f = s:fullFrame()
    local newY = p.y
    local changed = false

    if p.y <= f.y + EDGE_BLOCKER_DEADZONE_TOP then
      newY = f.y + EDGE_BLOCKER_DEADZONE_TOP + 2
      changed = true
    elseif p.y >= (f.y + f.h - EDGE_BLOCKER_DEADZONE_BOTTOM) then
      newY = f.y + f.h - EDGE_BLOCKER_DEADZONE_BOTTOM - 2
      changed = true
    end

    if changed then
      event:setProperty(hs.eventtap.event.properties.mouseEventDeltaY, 0)
      event:location({ x = p.x, y = newY })
      return true, { event }
    end

    return false
  end)

  EDGE_BLOCKER_TAP:start()
end

startEdgeBlocker()

-- watchdog: if the tap ever stops, restart it
EDGE_BLOCKER_WATCHDOG = hs.timer.doEvery(1, function()
  if EDGE_BLOCKER_TAP and not EDGE_BLOCKER_TAP:isEnabled() then
    startEdgeBlocker()
    hs.alert.show("Edge blocker restarted")
  end
end)

hs.alert.show("Edge blocker loaded")

