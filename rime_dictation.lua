-- lua/rime_dictation.lua
local M = {}

-- Constants
local SERVER_URL = "http://localhost:8081/toggle"
local DOUBLE_CLICK_TIMEOUT = 1 -- seconds (User preference)

function M.init(env)
    env.last_ctrl_release_time = 0
    env.name_space = env.name_space or ""
    log.error("Rime Dictation: Initialized")
end

function M.fini(env)
end
local LISTENING_TEXT = "Listening"
local RECOGNIZING_TEXT = "Recognizing"
function M.func(key, env)
    -- Check for Left Control (0xffe3) or Right Control (0xffe4)
    if key.keycode == 0xffe3 or key.keycode == 0xffe4 then
        if key:release() then
            -- On Key Release
            local now = os.time() + os.clock() -- High precision time
            local diff = now - env.last_ctrl_release_time
            
            if diff < DOUBLE_CLICK_TIMEOUT then
                -- Double click detected!
                
                -- Check previous state to toggle text
                if env.engine.context.input == LISTENING_TEXT then
                    env.engine.context.input = RECOGNIZING_TEXT
                else
                    env.engine.context:clear()
                    env.engine.context.input = LISTENING_TEXT
                end

                -- Call Python server
                local success, handle = pcall(io.popen, "curl -s -X POST " .. SERVER_URL)
                if not success or not handle then
                     log.error("Rime Dictation: io.popen failed or blocked!")
                     os.execute("curl -s -X POST " .. SERVER_URL .. " &")
                     return 1
                end

                local response = handle:read("*a")
                handle:close()
                
                if response and string.find(response, '"status": "stopped"') then
                     -- Do NOT clear context here; let commit_text replace it to keep Undo history clean
                     -- env.engine.context:clear()
                     
                     local text = string.match(response, '"text": "(.-)"')
                     if text then
                         env.engine:commit_text(text)
                     end
                     
                     -- Ensure context is clear after commit if commit didn't do it (safety check)
                     -- Only clear if it still says "Recognizing" (meaning commit failed or didn't replace)
                     if env.engine.context.input == RECOGNIZING_TEXT then
                        env.engine.context:clear()
                     end

                elseif response and string.find(response, '"status": "started"') then
                     env.engine.context:clear()
                     env.engine.context.input = LISTENING_TEXT
                end
                
                env.last_ctrl_release_time = 0 -- Reset
                return 1 -- kAccepted
            else
                env.last_ctrl_release_time = now
            end
        end
        return 0 -- kRejected
    end

    -- Cancel / Undo: Ctrl+Z or Alt+Z (keycode 'z' is 0x007a)
    if key.keycode == 0x007a and (key:ctrl() or key:alt()) then
        if env.engine.context.input == LISTENING_TEXT or env.engine.context.input == "⏳ Recognizing" then
            -- Cancel ongoing dictation
            env.engine.context:clear()
            os.execute("curl -s -X POST " .. SERVER_URL .. " &")
            return 1 -- Accepted, swallowed key
        end
        -- Otherwise pass through for standard Undo
        return 0
    end

    return 2 -- kNoop
end

return M
