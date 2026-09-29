hs.autoLaunch(true)

EDGE_BLOCKER_ENABLED = true
EDGE_BLOCKER_DEADZONE_TOP = 12
EDGE_BLOCKER_DEADZONE_BOTTOM = 16
EDGE_BLOCKER_TOGGLE_MODS = {"shift", "alt"}
EDGE_BLOCKER_TOGGLE_KEY = "k"
EDGE_BLOCKER_PASSWORD_SALT = "__PASSWORD_SALT__"
EDGE_BLOCKER_PASSWORD_HASH = "__PASSWORD_HASH__"
EDGE_BLOCKER_PASSWORD_ACTIVE = false
EDGE_BLOCKER_PASSWORD_INPUT = ""
EDGE_BLOCKER_PASSWORD_ALERT = nil
EDGE_BLOCKER_TOGGLE_KEY_DOWN = false

-- macOS virtual key codes for letters, digits, punctuation, space, Return,
-- keypad numbers/operations, and arrow keys. The ISO key at code 10 is
-- included for German and Swiss keyboard layouts.
ALLOWED_KEY_CODES = {}
for _, keyCode in ipairs({
  0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
  18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
  34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 49, 50,
  65, 67, 69, 75, 76, 78, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91,
  92, 123, 124, 125, 126
}) do
  ALLOWED_KEY_CODES[keyCode] = true
end

ALLOWED_MODIFIER_KEY_CODES = {
  [56] = true, -- left Shift
  [60] = true, -- right Shift
  [58] = true, -- left Alt/Option
  [61] = true  -- right Alt/Option
}

function closeEdgeBlockerPasswordPrompt()
  if EDGE_BLOCKER_PASSWORD_ALERT then
    hs.alert.closeSpecific(EDGE_BLOCKER_PASSWORD_ALERT, 0)
    EDGE_BLOCKER_PASSWORD_ALERT = nil
  end
  EDGE_BLOCKER_PASSWORD_ACTIVE = false
  EDGE_BLOCKER_PASSWORD_INPUT = ""
end

function updateEdgeBlockerPasswordPrompt()
  if EDGE_BLOCKER_PASSWORD_ALERT then
    hs.alert.closeSpecific(EDGE_BLOCKER_PASSWORD_ALERT, 0)
  end
  local length = utf8.len(EDGE_BLOCKER_PASSWORD_INPUT) or 0
  local bullets = string.rep("•", length)
  EDGE_BLOCKER_PASSWORD_ALERT = hs.alert.show(
    "Edge-Blocker deaktivieren\nPasswort: " .. bullets ..
      "\nEnter = bestätigen · Esc = abbrechen",
    { textSize = 18 },
    "indefinite"
  )
end

function startEdgeBlockerPasswordPrompt()
  EDGE_BLOCKER_PASSWORD_ACTIVE = true
  EDGE_BLOCKER_PASSWORD_INPUT = ""
  updateEdgeBlockerPasswordPrompt()
end

function removeLastPasswordCharacter()
  local lastCharacter = utf8.offset(EDGE_BLOCKER_PASSWORD_INPUT, -1)
  if lastCharacter then
    EDGE_BLOCKER_PASSWORD_INPUT = EDGE_BLOCKER_PASSWORD_INPUT:sub(1, lastCharacter - 1)
  end
end

function submitEdgeBlockerPassword()
  local enteredHash = hs.hash.SHA256(
    EDGE_BLOCKER_PASSWORD_SALT .. ":" .. EDGE_BLOCKER_PASSWORD_INPUT
  )
  closeEdgeBlockerPasswordPrompt()

  if enteredHash == EDGE_BLOCKER_PASSWORD_HASH then
    EDGE_BLOCKER_ENABLED = false
    hs.alert.show("Edge blocker: OFF")
  else
    hs.alert.show("Falsches Passwort")
  end
end

function edgeBlockerToggle()
  if EDGE_BLOCKER_ENABLED then
    startEdgeBlockerPasswordPrompt()
  else
    EDGE_BLOCKER_ENABLED = true
    hs.alert.show("Edge blocker: ON")
  end
end

function hasBlockedModifiers(flags)
  return flags.cmd or flags.ctrl or flags.fn
end

function isEdgeBlockerToggle(event)
  local flags = event:getFlags()
  return event:getKeyCode() == 40 and flags.shift and flags.alt and
    not hasBlockedModifiers(flags)
end

function handlePasswordKey(event)
  local eventType = event:getType()
  if eventType ~= hs.eventtap.event.types.keyDown then
    return true
  end

  local keyCode = event:getKeyCode()
  if keyCode == 36 or keyCode == 76 then
    submitEdgeBlockerPassword()
  elseif keyCode == 53 then
    closeEdgeBlockerPasswordPrompt()
    hs.alert.show("Abgebrochen")
  elseif keyCode == 51 or keyCode == 117 then
    removeLastPasswordCharacter()
    updateEdgeBlockerPasswordPrompt()
  elseif ALLOWED_KEY_CODES[keyCode] and not hasBlockedModifiers(event:getFlags()) then
    local characters = event:getCharacters(false)
    if characters and characters ~= "" then
      EDGE_BLOCKER_PASSWORD_INPUT = EDGE_BLOCKER_PASSWORD_INPUT .. characters
      updateEdgeBlockerPasswordPrompt()
    end
  end

  return true
end

function handleKeyboardEvent(event)
  if EDGE_BLOCKER_PASSWORD_ACTIVE then
    return handlePasswordKey(event)
  end

  local eventType = event:getType()
  if eventType == hs.eventtap.event.types.keyDown and isEdgeBlockerToggle(event) then
    local isRepeat = event:getProperty(
      hs.eventtap.event.properties.keyboardEventAutorepeat
    ) ~= 0
    if not isRepeat then
      EDGE_BLOCKER_TOGGLE_KEY_DOWN = true
      edgeBlockerToggle()
    end
    return true
  end

  if eventType == hs.eventtap.event.types.keyUp and
      event:getKeyCode() == 40 and EDGE_BLOCKER_TOGGLE_KEY_DOWN then
    EDGE_BLOCKER_TOGGLE_KEY_DOWN = false
    return true
  end

  if not EDGE_BLOCKER_ENABLED then
    return false
  end

  if eventType == hs.eventtap.event.types.systemDefined then
    return true
  end

  if eventType == hs.eventtap.event.types.flagsChanged then
    return not ALLOWED_MODIFIER_KEY_CODES[event:getKeyCode()]
  end

  if hasBlockedModifiers(event:getFlags()) then
    return true
  end

  return not ALLOWED_KEY_CODES[event:getKeyCode()]
end

function startKeyboardBlocker()
  if KEYBOARD_BLOCKER_TAP then
    KEYBOARD_BLOCKER_TAP:stop()
    KEYBOARD_BLOCKER_TAP = nil
  end

  KEYBOARD_BLOCKER_TAP = hs.eventtap.new({
    hs.eventtap.event.types.keyDown,
    hs.eventtap.event.types.keyUp,
    hs.eventtap.event.types.flagsChanged,
    hs.eventtap.event.types.systemDefined
  }, handleKeyboardEvent)
  KEYBOARD_BLOCKER_TAP:start()
end

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
startKeyboardBlocker()

-- watchdog: if a tap ever stops, restart it
EDGE_BLOCKER_WATCHDOG = hs.timer.doEvery(1, function()
  if EDGE_BLOCKER_TAP and not EDGE_BLOCKER_TAP:isEnabled() then
    startEdgeBlocker()
    hs.alert.show("Edge blocker restarted")
  end
  if KEYBOARD_BLOCKER_TAP and not KEYBOARD_BLOCKER_TAP:isEnabled() then
    startKeyboardBlocker()
    hs.alert.show("Keyboard blocker restarted")
  end
end)

hs.alert.show("Edge blocker loaded")
