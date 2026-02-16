# SongML Utils
Python utilities for working with SongML files - a relaxed, forgiving format for notating music like a musician's leadsheet.

## Installation

```bash
pip install songml-utils --break-system-packages --user
```

## CLI Commands

All commands support `--help` for detailed usage information:

- **songml-create** - Create a new SongML project from template
- **songml-format** - Format SongML files with aligned bar markers
- **songml-validate** - Parse and validate SongML, output AST as JSON
- **songml-to-midi** - Convert SongML to MIDI using chord voicings
- **songml-inspect-midi** - Inspect MIDI files and display their properties
- **songml-to-abc** - Convert SongML to ABC notation format
- **songml-serve** - Start a web server for viewing SongML files
- **songml-bashcompletion** - Generate bash completion script

### Bash Completion

Enable tab completion for all songml commands:

```bash
songml-bashcompletion > ~/.config/bash_completion.d/songml
source ~/.config/bash_completion.d/songml
```

Or add to `~/.bashrc`:
```bash
source ~/.config/bash_completion.d/songml
```

## Usage

```python
from songml_utils import parse_songml, format_songml
```

## LLM Context

[../docs/songml_design_manifesto.md] is a good starting context file.
