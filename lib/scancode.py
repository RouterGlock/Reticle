#!/usr/bin/env python3
"""
scancode - decode QR / Aztec / Data Matrix / PDF417 / 1-D barcodes from image files.

Usage:
    scancode IMAGE [IMAGE ...]          decode one or more image files
    scancode -j IMAGE                   JSON output
    scancode -v IMAGE                   verbose: show which preprocessing pass hit
    scancode --formats                  list supported symbologies

Exit status: 0 if at least one code was found in every file, 1 otherwise.
"""
import sys
import os
import json
import argparse

import numpy as np
import cv2
import zxingcpp


PASSES = ["original"]


def _variants(gray):
    """Yield (tag, image) preprocessing attempts, cheapest first."""
    h, w = gray.shape
    yield "original", gray

    big = max(h, w)
    for scale in (2.0, 3.0, 0.5):
        nw, nh = int(w * scale), int(h * scale)
        if 40 <= nw <= 8000 and 40 <= nh <= 8000:
            interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
            yield f"scale x{scale}", cv2.resize(gray, (nw, nh), interpolation=interp)

    # contrast + Otsu on a mild upscale
    up = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC) if big < 1600 else gray
    _, otsu = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    yield "otsu", otsu

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(up)
    yield "clahe", clahe
    _, clahe_otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    yield "clahe+otsu", clahe_otsu

    blur = cv2.GaussianBlur(up, (0, 0), 3)
    sharp = cv2.addWeighted(up, 1.8, blur, -0.8, 0)
    yield "sharpen", sharp

    for angle in (90, 180, 270):
        yield f"rot {angle}", np.rot90(gray, k=angle // 90)


def decode_file(path, verbose=False):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return {"file": path, "error": "cannot read image"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    seen = {}
    for tag, variant in _variants(gray):
        try:
            results = zxingcpp.read_barcodes(variant)
        except Exception as e:  # noqa: BLE001
            if verbose:
                print(f"  [{tag}] error: {e}", file=sys.stderr)
            continue
        for r in results:
            key = (str(r.format), r.text)
            if key not in seen:
                seen[key] = {
                    "format": str(r.format),
                    "text": r.text,
                    "valid": bool(r.valid),
                    "via": tag,
                }
        if seen and tag == "original":
            break  # clean hit, no need to grind through fallbacks

    return {"file": path, "codes": list(seen.values())}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scancode", add_help=True,
                                 description=__doc__.strip().splitlines()[0])
    ap.add_argument("images", nargs="*", help="image file(s) to decode")
    ap.add_argument("-j", "--json", action="store_true", help="JSON output")
    ap.add_argument("-v", "--verbose", action="store_true", help="show decode passes")
    ap.add_argument("--formats", action="store_true", help="list supported symbologies")
    args = ap.parse_args(argv)

    if args.formats:
        print("QR Code, Micro QR, rMQR, Aztec, Data Matrix, PDF417, MaxiCode,\n"
              "Code 128, Code 93, Code 39, Codabar, ITF, DataBar,\n"
              "EAN-13, EAN-8, UPC-A, UPC-E")
        return 0

    if not args.images:
        ap.print_help()
        return 1

    reports = [decode_file(p, args.verbose) for p in args.images]

    if args.json:
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))
    else:
        for rep in reports:
            name = os.path.basename(rep["file"])
            if rep.get("error"):
                print(f"{name}: ERROR - {rep['error']}")
                continue
            if not rep["codes"]:
                print(f"{name}: no code found")
                continue
            for c in rep["codes"]:
                line = f"{name}: [{c['format']}] {c['text']}"
                if not c["valid"]:
                    line += "  (checksum not validated)"
                if args.verbose:
                    line += f"  <via {c['via']}>"
                print(line)

    ok = all(r.get("codes") for r in reports)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
