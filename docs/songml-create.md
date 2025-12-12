# songml-create

Command-line tool for creating new SongML projects with templated structure.

## Usage

```bash
songml-create "Song Name" [root][min]
```

## Arguments

- `"Song Name"`: The title of your song (use quotes if it contains spaces)
- `[root][min]`: Key specification where:
  - `root` is a note name: C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B
  - `min` is optional suffix for minor keys

## Examples

```bash
# Create a song in C major
songml-create "My Song" C

# Create a song in F# minor
songml-create "Sad Ballad" F#min

# Create a song in Bb major
songml-create "Jazz Standard" Bb

# Create a song in D minor
songml-create "Dark Theme" Dmin
```

## Project Structure

The command creates a project directory with the sanitized song name containing:

```
my-song/
├── chord_voicings.tsv    # Chord voicing definitions (copy for local customization)
└── my-song.songml        # Main SongML file with template structure
```

## Template Structure

The generated SongML file includes:

- **Intro**: 4-bar I-vi-IV-V progression
- **Verse**: 8-bar verse with placeholder lyrics
- **Chorus**: 8-bar chorus with placeholder lyrics  
- **Bridge**: 4-bar bridge section
- **Outro**: 4-bar ending

All chord progressions use basic triads appropriate for the specified key.

## Key Support

### Major Keys
Supports all 12 major keys: C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B

### Minor Keys  
Supports all 12 minor keys by adding `min` suffix: Amin, C#min, Dmin, F#min, etc.

## Name Sanitization

Project names are automatically sanitized for file system compatibility:
- Converted to lowercase
- Spaces become dashes
- Windows forbidden characters (`<>:"/\|?*`) become dashes
- Multiple consecutive separators become single dashes
- Leading/trailing dashes removed

Examples:
- `"My Song"` → `my-song`
- `"Song: With/Special\\Chars"` → `song--with-special-chars`

## Error Handling

The command will exit with error code 1 if:
- Invalid key format is provided
- Project directory already exists
- Template files are missing
- File system errors occur

## See Also

- [SongML Syntax](songml-syntax.md) - Language reference
- `songml-validate` - Validate SongML syntax
- `songml-to-midi` - Export SongML to MIDI
