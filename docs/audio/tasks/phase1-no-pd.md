## Phase 1 Audio Tasks - No Pure Data Required

This document lists tasks from `phase1-audio.md` that can be completed without Pure Data installed.

**Note:** Pure Data patch files (.pd) are plain text files with documented syntax. They can be created using the Write tool without Pd installed.

### Implementation Summary

**Completable without Pd:** 83 of 93 tasks (89%)
**Requires Pd installed and running:** 10 tasks (11%)

---

## Component 0: Prerequisites (4 of 6 tasks)

- [ ] **Task 0.1**: Verify Python 3.8+ installed
- [ ] **Task 0.2**: Install python-osc package
- [ ] **Task 0.5**: Verify sample library exists
- [ ] **Task 0.6**: Verify testing infrastructure exists

**Cannot do without Pd:**
- Task 0.3: Pure Data installation
- Task 0.4: Audio interface configuration (requires Pd for testing)

---

## Component 1: Project Structure (2 of 2 tasks)

- [ ] **Task 1.1**: Create directory structure
- [ ] **Task 1.2**: Create audio README

---

## Component 2: Test Infrastructure Scripts (13 of 14 tasks)

### test-osc-sender.py
- [ ] **Task 2.1**: Create test-osc-sender.py skeleton
- [ ] **Task 2.2**: Implement IBI generation
- [ ] **Task 2.3**: Implement sensor threads
- [ ] **Task 2.4**: Implement OSC sending
- [ ] **Task 2.5**: Implement signal handling
- [ ] **Task 2.6**: Test test-osc-sender.py (standalone, no Pd needed)

### install-dependencies.sh
- [ ] **Task 2.7**: Create install-dependencies.sh
- [ ] **Task 2.8**: Implement Pd installation
- [ ] **Task 2.9**: Implement externals installation
- [ ] **Task 2.10**: Test install-dependencies.sh

### detect-audio-interface.sh
- [ ] **Task 2.11**: Create detect-audio-interface.sh
- [ ] **Task 2.12**: Implement USB interface detection
- [ ] **Task 2.13**: Implement fallback and testing

**Cannot do without Pd:**
- Task 2.14: Test detect-audio-interface.sh (speaker-test works, but Pd integration test requires Pd)

---

## Component 10: Documentation & Completion (10 of 10 tasks)

- [ ] **Task 10.1**: Create sample library README
- [ ] **Task 10.2**: Document Pd patch architecture
- [ ] **Task 10.3**: Document testing procedures
- [ ] **Task 10.4**: Verify all acceptance criteria
- [ ] **Task 10.5**: Validate audio and sample requirements
- [ ] **Task 10.6**: Validate OSC protocol implementation
- [ ] **Task 10.7**: Validate Pd patch structure
- [ ] **Task 10.8**: Validate support scripts
- [ ] **Task 10.9**: Validate disconnection handling
- [ ] **Task 10.10**: Update completion status

**Note:** Documentation can be written without Pd, but final validation requires Pd running.

---

## Components Implementable as Text Files (No Pd Installation Needed)

Pure Data patches are text files. The following can be created without Pd installed:

- **Component 3**: Main Patch Structure (3 tasks) ✓
- **Component 4**: OSC Input Subpatch (4 tasks) ✓
- **Component 5**: Sensor Processing Subpatch (9 tasks) ✓
- **Component 6**: Sound Engine Subpatch (9 tasks) ✓
- **Component 7**: Spatial Mixer Subpatch (8 tasks) ✓
- **Component 8**: Lighting Output Subpatch (6 tasks) ✓

**Total:** 39 patch creation tasks can be completed as text files

## Components Requiring Pure Data Running

- **Component 9**: Testing (10 tasks) - requires Pd to execute patches

**Total:** Only 10 tasks require Pd installed and running

---

## Recommended Implementation Order (No Pd)

1. **Prerequisites** (Tasks 0.1, 0.2, 0.5, 0.6)
2. **Project Structure** (Tasks 1.1, 1.2)
3. **Python Test Script** (Tasks 2.1-2.6)
4. **Bash Scripts** (Tasks 2.7-2.13)
5. **Patch Files** (Components 3-8: Tasks 3.1-8.6)
   - Write all .pd files as text using documented format
6. **Documentation** (Tasks 10.1-10.3)

After Pd is installed, complete Component 9 (integration testing) and final validation (10.4-10.10).

---

## Value of No-Pd Implementation

Completing these 83 tasks provides:

1. **Directory structure** ready for deployment
2. **All .pd patch files** created as text (Components 3-8)
3. **Test infrastructure** for immediate Pd testing when installed
4. **Installation automation** for quick Pd setup
5. **Audio configuration** helpers for ALSA
6. **Complete documentation** for implementation and testing

This completes 89% of Phase 1, leaving only integration testing for when Pd is installed.

---

## Testing Without Pd

You can validate the following without Pd:

- `test-osc-sender.py` sends OSC messages (capture with Wireshark or netcat)
- `install-dependencies.sh` runs without errors
- `detect-audio-interface.sh` creates `.asoundrc` correctly
- `.pd` files have valid syntax (manual inspection)
- Directory structure matches TRD specification
- Sample files exist and meet format requirements
- Documentation is complete and accurate

**Patch syntax validation:**
- Verify `#N canvas` headers
- Check `#X obj` coordinate consistency
- Validate `#X connect` references match object count
- Ensure semicolons terminate all lines

---

## Next Steps After This Phase

Once these 83 tasks are complete:

1. Run `install-dependencies.sh` to install Pure Data
2. Open patches in Pd to verify syntax correctness
3. Complete Component 9 (integration testing with live Pd)
4. Finalize Component 10 (validation and acceptance criteria)

**Testing workflow:**
1. Start Pd with `heartbeat-main.pd`
2. Run `test-osc-sender.py` to send test messages
3. Verify audio output and stereo positioning
4. Monitor lighting OSC with `osc_receiver.py`
5. Run 30-minute stability test
