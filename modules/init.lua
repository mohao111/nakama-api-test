local nk = require("nakama")

-- Create the test leaderboard at load time.
-- Signature: leaderboard_create(id, authoritative, sort, operator, reset, metadata)
--   authoritative=false -> clients may submit scores directly (easy to test)
--   sort="desc"         -> higher score ranks first
--   operator="best"     -> keep each user's highest score
-- pcall keeps this idempotent: Postgres persists the leaderboard, so on the
-- next server start the create fails with "already exists" and we ignore it.
local ok, err = pcall(function()
    nk.leaderboard_create("test_leaderboard", false, "desc", "best", "", {})
end)
nk.logger_info("init.lua: ensure test_leaderboard ok=" .. tostring(ok) .. " err=" .. tostring(err))
