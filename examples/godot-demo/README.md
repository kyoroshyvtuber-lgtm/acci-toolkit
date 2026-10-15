# Headless Godot integration fixture

A small source fixture, not a finished game. `score.gd` implements bounded
collection/reset; `tests/score_test.gd` checks initialization, collection, limit
and reset, returning nonzero on failure.

The root Godot workflow imports, tests, exports a `.pck`, launches it with the
matching checksum-verified editor/runtime and preserves logs/hash/package.
No export templates are required for this resource-pack check.

See [game profiles](../../docs/GAMES.md) for iOS and Unity boundaries.