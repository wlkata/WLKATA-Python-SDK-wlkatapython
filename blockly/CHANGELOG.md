# Changelog

## v0.0.3

### Features
- **3D Model Viewer**: Embedded A-Frame robot viewer with per-variable tabs and motion animation playback
- **Animated Progress Bar**: Real-time progress bar showing action duration (e.g. 1.1s/3.0s) and interval countdown, replacing debug text overlays
- **Function Blocks with Local Variables**: Custom function definition blocks with parameter default values, local variable get/set blocks, and custom "V" icon menu
- **Local Instance Method Calls**: `local_instance_call` block auto-detects methods on locally declared instance variables within functions
- **Global Instance Method Detection**: `instance_function_call` now works with variables assigned from function return values (e.g. `asd = do_something()`)
- **App Icon**: Added icon and electron-builder icon configuration

### Bug Fixes
- Fix per-variable animation state isolation — multiple model viewers no longer interfere with each other
- Fix view tab highlight incorrectly reverting to Blockly tab when code changes trigger tab rebuild
- Fix default parameter inputs duplicating on every keystroke when renaming parameters
- Fix `local_instance_call` generating invalid Python (`a....()`) when method dropdown is unset
- Fix instance method detection failing after first call block by stripping method calls from inspection code
- Fix functions without `return` statement incorrectly creating model viewer tabs
- Remove all `global` declarations from generated Python in custom functions

### Internal
- Added `analyzeRobotCode()` state machine parser for code structure analysis
- Added `preprocessCodeForInspection()` for flattening function-return assignments
- Added `extractMovesFromLines()` shared move-extraction helper
- Refactored animation system from shared globals to per-variable state
- Removed `sample.js`

## v0.0.2

- Blockly now supports `*args` and `**kwargs`
- Server will now choose an available port when port 5080 is in use
