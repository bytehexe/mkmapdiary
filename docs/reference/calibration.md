# Calibration files

A `calibration.yaml` describes how to interpret the media in the directory that holds
it: what timezone its clock was set to, how far that clock had drifted, what image
effects to apply, and who made the media.

These files are optional. A source tree with none of them is read as system-local time
with no offset, no effects and no creator.

Write them by hand, or with [`mkmapdiary calibrate`](commands.md#calibrate).

## Format

```yaml
calibration:
  timezone: Europe/Berlin
  offset: -259
effects:
  - autorotate
creator: Janna Hopp
```

### `calibration`

The camera clock. If the block is present, both keys must be given — a nested file
cannot change the timezone while inheriting the offset. Omit the block entirely to
inherit both.

- `timezone`: the timezone the camera's own clock was set to, as an IANA name
  (`Europe/Berlin`, `Asia/Tokyo`, `UTC`, `Etc/GMT-3`). This is *not* where the photo was
  taken — it is what the camera believed the time was.
- `offset`: seconds of drift, as an integer. Positive means the camera clock ran ahead
  of true time; the offset is subtracted when the reading is converted.

Together these turn a wall-clock EXIF reading into an absolute instant, which is what
geo-correlation against GPX tracks needs.

### `effects`

A list of per-directory image effects. Currently the only supported value is
`autorotate`.

### `creator`

The name of whoever made the media in this directory — photographer, writer, whoever
held the recorder. It appears on the [credits page](credits.md), and next to each
asset's time and place, though the per-asset display is suppressed when a journal has
only one distinct creator, since repeating one name on every photo says nothing.

For images, this wins over any `Artist`, `By-line` or `XMP:Creator` tag in the file's
own metadata. Those tags are used only where a calibration file does not set a creator.

Merged GPX tracks are stitched together from many source files, so they carry no single
creator. The creators of the *source* track files are still named on the credits page.

## The calibration stack

Calibration is scoped to a subtree, not to a file. When the scan enters a directory
containing a `calibration.yaml`, that calibration is pushed onto a stack and applies to
everything below; when the scan leaves the directory, it is popped.

This means a single file at the root of a trip calibrates the whole trip, and a file
deeper down overrides it for that branch only:

```text
trip/
  calibration.yaml          # Europe/Berlin, creator: Janna Hopp
  day1/
    IMG_0001.jpg            # Europe/Berlin, Janna Hopp
  day2/
    calibration.yaml        # calibration: {timezone: Asia/Tokyo, offset: 0}
    IMG_0002.jpg            # Asia/Tokyo, Janna Hopp
```

## Inheritance

Top-level keys are inherited individually. A nested file overrides only what it names,
and everything it leaves out keeps the enclosing value — which is why `day2` above
changes the clock without losing the creator.

**Absent is not the same as null.** Omitting a key inherits it; setting it to `null`
clears it for that subtree:

```yaml
# trip/borrowed-camera/calibration.yaml
creator: null      # explicitly unattributed, despite trip/ naming a creator
```

`mkmapdiary calibrate creator --unset` writes exactly this. Deleting the line instead
would silently restore the inherited name.
