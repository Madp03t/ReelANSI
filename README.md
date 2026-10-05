# ReelANSi

ReelANSi is a lightweight Linux application for viewing, browsing, and
playing ANSI/textmode artwork and animations.

Open an individual textmode file or an entire folder, then browse
supported files without repeatedly opening and closing files.

ReelANSi is strictly a viewer, not an editor.

## Current Features

### ANSI Rendering

-   CP437 ANSI artwork
-   IBM VGA 9×16 font rendering
-   Classic 16-color VGA palette
-   Correct DOS/VGA foreground intensity handling
-   SAUCE metadata, author/date, and artwork dimensions
-   Pixel-crisp rendering without text antialiasing
-   Viewport-aware painting for very tall artwork
-   Scroll artwork larger than the viewing area
-   Large ANSI loading/loaded indicator

### Files & Browsing

-   Open individual `.ANS`, `.ASC`, and `FILE_ID.DIZ` files
-   Open/select a folder containing supported textmode files
-   Automatically browse supported files in the same folder
-   `FILE_ID.DIZ` presented first when present
-   Previous / Next navigation with wraparound
-   Left/right arrow keyboard navigation
-   Clickable Previous / Next controls
-   Display the current filename and artwork dimensions
-   Display SAUCE author/date when available
-   Display the full folder path
-   Display the current file position within the folder
-   Reset artwork view to the top-left when changing files

### Animation & Playback

-   Progressive ANSI stream playback
-   Automatic ansimation detection and playback
-   Play / Pause / Restart controls
-   Historical modem/BBS playback speeds from 300 baud through 230.4K
-   Instant playback for non-animated artwork
-   ANSI-encoded timing and padding respected during playback
-   Cursor movement, positioning, clearing, and screen overwrites during
    playback
-   Automatic viewport following during progressive playback, including
    tall ANSI files

### Interface

-   F11 maximized / normal window toggle
-   Remembers normal window size and maximized state
-   Remembers playback speed
-   Horizontally centers artwork narrower than the viewport
-   Minimal interface focused on the artwork

## In Development

-   Continued ANSI rendering fidelity testing against known-good scene
    artwork
-   Additional ANSI/iCE color and blink compatibility testing
-   XBin (`.XB`) support
-   Further ansimation compatibility testing, including tall animations

## Status

Early development. ANSI rendering, mixed textmode folder browsing,
progressive playback, and ANSI animation playback are working.
