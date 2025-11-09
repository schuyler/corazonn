# Pure Data Troubleshooting: Debugging Methodology

General approach to identifying and fixing issues in Pure Data patches.

**Related guides**: [Patch Creation](troubleshooting-patch-creation.md), [Timing & Performance](troubleshooting-timing-performance.md)

## General Debugging Approach

1. **Isolate the problem**:
   - Create minimal patch that reproduces issue
   - Remove everything not related to problem

2. **Add debug outputs**:
   - `[print LABEL]` for messages
   - `[print~ ]` for signals
   - Number boxes to visualize values

3. **Check signal flow**:
   - Verify connections made (drag, don't click)
   - Signal (thick) vs message (thin) lines
   - Right object types (~ for audio)

4. **Verify external dependencies**:
   - Libraries declared: `[declare -lib libname]`
   - Paths set: `[declare -path /path]`
   - Files exist: `ls -l filename.wav`

5. **Check Pd console**:
   - Red text = errors
   - Click error to jump to problem
   - "Find Last Error" in Find menu

6. **Test incrementally**:
   - Build patch in small steps
   - Test after each addition
   - Comment out sections to isolate issue

7. **Use help patches**:
   - Right-click object → Help
   - Shows example usage
   - Working reference implementation
