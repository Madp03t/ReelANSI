# ReelANSI

ReelANSI is a lightweight Linux application for viewing, browsing, and playing ANSI artwork and animations.

Open an individual ANSI file or an entire folder, then browse the other ANSI files without repeatedly opening and closing files.

ReelANSI is strictly a viewer, not an editor.

## Current Features

### ANSI Rendering
- CP437 ANSI artwork
- IBM VGA 9×16 font rendering
- Classic 16-color VGA palette
- SAUCE metadata and artwork dimensions
- Pixel-crisp rendering without text antialiasing
- Scroll artwork larger than the viewing area

### Files & Browsing
- Open individual `.ANS` files
- Open/select a folder containing ANSI files
- Automatically browse other ANSI files in the same folder
- Previous / Next navigation with wraparound
- Left/right arrow keyboard navigation
- Clickable Previous / Next controls
- Display the current filename and artwork dimensions
- Display the full folder path
- Display the current file position within the folder
- Reset artwork view to the top-left when changing files

### Animation
- Progressive ANSI stream playback
- Play / Pause / Restart controls
- Historical modem/BBS playback speeds from 300 baud through 56K
- Instant playback
- ANSI-encoded timing and padding respected during playback
- Cursor movement, positioning, clearing, and screen overwrites during playback

## In Development

### Interface
- Fullscreen viewing
- Minimal interface focused on the artwork

## Status

Early development. ANSI rendering, folder-based browsing, and ANSI animation playback are working.
