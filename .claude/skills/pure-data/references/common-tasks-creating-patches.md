# Creating Patches

Quick reference for creating Pure Data subpatches and abstractions.

## Create a New Subpatch

1. In parent patch: Add object `[pd subpatch-name]`
2. Right-click → Open to edit
3. Add `[inlet]` for each input from parent
4. Add `[outlet]` for each output to parent
5. Implement logic
6. Close window (saves automatically)
7. Connect inlets/outlets in parent patch

**When to use**: Logic that's specific to one patch, doesn't need to be reused.

## Create a New Abstraction

1. Create new file: `abstraction-name.pd`
2. Add `[inlet]` and `[outlet]` objects as needed
3. Use `$1, $2, $3...` for creation arguments
4. Use `$0-local-name` for instance-specific send/receive
5. Save in `audio/patches/` directory
6. Use in parent: `[abstraction-name arg1 arg2]`

**When to use**: Logic that needs multiple instances with different parameters (like sensor-process.pd).

**Example**: `sensor-process.pd` is instantiated 4 times: `[sensor-process 0]`, `[sensor-process 1]`, etc.

---

**Related documentation**:
- See common-tasks-integration-setup.md for declaring externals and paths
