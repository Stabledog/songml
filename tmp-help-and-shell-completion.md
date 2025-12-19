# Help System and Shell Completion Plan

## Overview
Add comprehensive help system and bash completion support for songml CLI tools.

**Implementation**: Python-based CLI with entry points defined in `pyproject.toml`

**Constraints**:
- Do NOT change existing CLI behavior
- Only add help text for existing features
- Keep help minimal (reminders, not tutorials)
- This is not a refactoring exercise

## Part A: Help System (`--help` / `-h`)

### Design Principles
- Minimal, reminder-style help text
- Show what the command does and basic usage
- 1-2 simple examples maximum
- Use Python's `argparse` for consistent help formatting

### Audit and Document Phase

**Step 1**: Examine each CLI module to document:
1. Current arguments and their purpose
2. Any existing argparse setup
3. Actual behavior and constraints

**Step 2**: Add argparse help where missing or incomplete
- Only document what exists
- Keep descriptions brief
- Provide minimal examples

### Commands to Audit

#### 1. `songml-create` (`songml_utils.create:main`)
#### 2. `songml-format` (`songml_utils.formatter:main`)
#### 3. `songml-validate` (`songml_utils.validate:main`)
#### 4. `songml-to-midi` (`songml_utils.midi_cli:main`)

### Implementation Pattern

```python
def main():
    parser = argparse.ArgumentParser(
        description="[Brief one-line purpose]",
        epilog="""Examples:
  %(prog)s [example based on actual usage]""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Add help text to existing arguments only
    parser.add_argument('existing_arg', help='[brief description]')
    # ...
```

## Part B: Shell Completion

### New Command: `songml-bashcompletion`

**Implementation**: New Python module `songml_utils.bashcompletion:main`

**Purpose**: Generate bash completion script for all songml-* commands

**Usage**:
```bash
songml-bashcompletion   # Output bash completion script to stdout
```


### Completion Features

Based on actual CLI implementations, generate completion for:
1. All `songml-*` commands (including `songml-bashcompletion` itself)
2. All options/flags for each command
3. File completion filtered to `.songml` files where appropriate
4. Context-aware completion after options that take values

### Implementation Approach

The `bashcompletion.py` module will:
1. Define completion data for each command (self-contained, hardcoded)
2. Use a bash script template
3. Generate complete, ready-to-use bash completion script
4. Output to stdout for easy installation
5. Include installation instructions in its own help text

## Files to Create/Modify

### New Files
1. `songml-utils/src/songml_utils/bashcompletion.py` - Bash completion script generator

### Files to Modify
1. `songml-utils/pyproject.toml` - Add entry point for `songml-bashcompletion`
2. Potentially each CLI module (only if argparse help is missing/incomplete):
   - `songml-utils/src/songml_utils/create.py`
   - `songml-utils/src/songml_utils/formatter.py`
   - `songml-utils/src/songml_utils/validate.py`
   - `songml-utils/src/songml_utils/midi_cli.py`

## Implementation Plan

### Phase 1: Audit ✅ COMPLETE
- [x] Review `create.py` - document current args and behavior
- [x] Review `formatter.py` - document current args and behavior
- [x] Review `validate.py` - document current args and behavior
- [x] Review `midi_cli.py` - document current args and behavior
- [x] Document findings in this plan

#### Audit Findings

**1. `songml-create` (create.py)**
- **Current args**: `SONG_NAME KEY` (2 positional args required)
- **Argparse**: ❌ No argparse, manual sys.argv parsing
- **Help text**: Has usage examples in main() but not accessible via --help
- **Behavior**: Creates project directory with .songml file and chord_voicings.tsv
- **Exit codes**: 0=success, 1=errors

**2. `songml-format` (formatter.py)**
- **Current args**: `INPUT.songml [OUTPUT.songml|-i|--inplace]`
- **Argparse**: ❌ No argparse, manual sys.argv parsing
- **Help text**: Has usage examples in main() but not accessible via --help
- **Behavior**: Formats SongML by aligning | markers. Defaults to stdout.
- **Exit codes**: 0=success, 1=errors
- **Options**: `-i` or `--inplace` for in-place editing

**3. `songml-validate` (validate.py)**
- **Current args**: `FILE.songml` (1 positional arg required)
- **Argparse**: ❌ No argparse, manual sys.argv parsing
- **Help text**: Has basic usage in main() but not accessible via --help
- **Behavior**: Parses SongML, outputs AST JSON to stdout, messages to stderr
- **Exit codes**: 0=success, 1=errors

**4. `songml-to-midi` (midi_cli.py)**
- **Current args**: `INPUT.songml OUTPUT.mid` (2 positional args required)
- **Argparse**: ❌ No argparse, manual sys.argv parsing
- **Help text**: Has usage in main() but not accessible via --help
- **Behavior**: Converts SongML to MIDI using chord voicing table
- **Exit codes**: 0=success, 1=errors

#### Summary
- All 4 commands use manual sys.argv parsing (no argparse)
- All have basic usage/examples in code but no --help support
- All are simple and well-structured
- Adding argparse will require minimal changes to maintain existing behavior

### Phase 2: Help Implementation ✅ COMPLETE
- [x] Add/enhance argparse help in each module (minimal changes)
- [x] Test help output for all commands
- [x] Ensure `-h` and `--help` work consistently

All 4 commands now support `--help` with:
- Brief description of purpose
- Argument documentation
- Usage examples
- Redundant usage comments removed from docstrings

### Phase 3: Completion Implementation ✅ COMPLETE
- [x] Create `bashcompletion.py` module
- [x] Implement bash script generation (hardcoded completion data)
- [x] Add entry point to `pyproject.toml`
- [x] Test completion script generation
- [x] Document installation instructions in help

Created `songml-bashcompletion` command that generates a bash completion script with:
- Completion for all 5 songml-* commands (including itself)
- Option completion (-h, --help, -i, --inplace)
- File completion filtered to .songml files where appropriate
- Context-aware completion for songml-to-midi (.songml then .mid)
- Installation instructions in --help output

## Decision Summary

1. **Completion data source**: **A** - Self-contained with hardcoded command/option lists
   - Simpler implementation
   - Easy to maintain given the small number of commands
   - Aligns with songml's pragmatic philosophy

2. **Help vs behavior**: **A** - Add basic argparse without changing behavior if needed
   - Only if the changes are minimal
   - Skip if it requires significant refactoring

3. **Completion installation docs**: **C** - Both
   - Brief instructions in `songml-bashcompletion --help`
   - Detailed documentation in README or docs

## Implementation Complete! ✅

All phases successfully completed:

### Summary of Changes

**Files Created:**
- `songml-utils/src/songml_utils/bashcompletion.py` - New bash completion generator

**Files Modified:**
- `songml-utils/src/songml_utils/create.py` - Added argparse help
- `songml-utils/src/songml_utils/formatter.py` - Added argparse help
- `songml-utils/src/songml_utils/validate.py` - Added argparse help
- `songml-utils/src/songml_utils/midi_cli.py` - Added argparse help
- `songml-utils/pyproject.toml` - Added songml-bashcompletion entry point
- `songml-utils/README.md` - Added CLI commands section

**Key Features:**
- All 5 commands now support `--help` and `-h`
- Minimal, reminder-style help text (not tutorials)
- Bash completion script with:
  - Command and option completion
  - Context-aware file completion (.songml, .mid)
  - Easy installation instructions
- Existing behavior preserved (no breaking changes)
- Redundant usage comments removed from docstrings

**Testing Verified:**
- ✅ All --help outputs display correctly
- ✅ Commands work normally with argparse
- ✅ songml-create creates projects correctly
- ✅ Bash completion script generates successfully
- ✅ Package installs and runs as expected

### Usage Examples

```bash
# Get help for any command
songml-create --help
songml-format --help

# Install bash completion
songml-bashcompletion > ~/.config/bash_completion.d/songml
source ~/.config/bash_completion.d/songml

# Use the commands (unchanged behavior)
songml-create "My Song" C
songml-format song.songml -i
songml-validate song.songml
songml-to-midi song.songml song.mid
```
