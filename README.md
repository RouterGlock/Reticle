# Reticle

Read the code your phone can't. Reticle decodes **QR, Aztec, Data Matrix,
PDF417 and the common 1‑D barcodes** from an image — and tells you *which*
symbology it found. Built after a venue wristband turned out to carry an Aztec
code, which most phone camera apps silently ignore because they only hunt for QR.

Two front ends, one decoder core ([zxing-cpp](https://github.com/zxing-cpp/zxing-cpp)):

| | |
|---|---|
| **`scancode`** | command-line decoder for image files (macOS/Linux) |
| **`web/reticle.html`** | single-file browser app — live camera + drop/paste a photo, nothing leaves the page |

## CLI

```
./install.sh                 # creates ~/.local/share/reticle/venv, installs `scancode`
```

```
scancode IMAGE [IMAGE ...]   # decode one or more images
scancode -j IMAGE            # JSON output
scancode -v IMAGE            # verbose: report which preprocessing pass succeeded
scancode --formats           # list supported symbologies
```

Exit status is `0` only if every file yielded at least one code.

```
$ scancode wristband.jpeg
wristband.jpeg: [Aztec] 048275163

$ scancode -v qr_photo.jpg
qr_photo.jpg: [QR Code] https://example.com/kit?id=048275163  <via original>
```

### How it decodes

`scancode` hands the raw image to zxing-cpp first. If nothing is found it grinds
through a ladder of preprocessing passes — 2×/3×/0.5× rescales, Otsu threshold,
CLAHE local-contrast, unsharp mask, and 90/180/270° rotations — stopping at the
first pass that reads a code. Clean images resolve on the first try; crumpled,
glare-lit, or rotated photos usually fall out a few rungs down.

## Web app

Open `web/reticle.html` in any modern browser, or host it anywhere static.
It loads the [`@zxing/library`](https://github.com/zxing-js/library) UMD build
from a CDN and runs entirely client-side: camera frames and dropped images are
decoded in the page and never uploaded. Scan history is kept in `localStorage`
on that device only.

## Layout

```
bin/scancode        thin wrapper -> ~/.local/share/reticle/venv
lib/scancode.py     the CLI (argparse + preprocessing ladder)
web/reticle.html    the browser app (self-contained)
install.sh          venv setup + copy into ~/.local/bin
requirements.txt    zxing-cpp, numpy, opencv-python-headless
```

## Supported symbologies

QR Code · Micro QR · rMQR · Aztec · Data Matrix · PDF417 · MaxiCode ·
Code 128 · Code 93 · Code 39 · Codabar · ITF · DataBar · EAN‑13/8 · UPC‑A/E

## License

MIT
