#!/usr/bin/env python3
"""Build the installable PWA in docs/ from web/reticle.html.

The web app loads its decoder from a CDN, which is fine for a page you open
now and then. An installed app has to launch on a cold subway platform, so the
PWA build inlines the vendored decoder and precaches everything in a service
worker. Same source, no second copy to keep in sync.

    python3 tools/build-pwa.py

Writes docs/index.html. The rest of docs/ (manifest, icons, sw.js) is checked
in and edited by hand.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "web/reticle.html"
LIB = ROOT / "vendor/zxing-library-0.21.3.umd.min.js"
OUT = ROOT / "docs/index.html"

# The app script's opening lines — the inlined library is spliced in above it,
# so window.ZXing exists before the loader looks for it.
APP_SCRIPT = '<script>\n(function () {\n  "use strict";'

PWA_HEAD = """<link rel="manifest" href="./manifest.webmanifest" />
<meta name="theme-color" content="#eef1f2" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0e1214" media="(prefers-color-scheme: dark)" />
<meta name="mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="apple-mobile-web-app-title" content="Reticle" />
<link rel="apple-touch-icon" href="./apple-touch-icon.png" />
<link rel="icon" href="./favicon-32.png" sizes="32x32" />
<link rel="icon" href="./icon.svg" type="image/svg+xml" />
<style>
  /* Keep content clear of the notch and the home indicator. */
  .wrap {
    padding-left: max(20px, env(safe-area-inset-left));
    padding-right: max(20px, env(safe-area-inset-right));
    padding-top: max(32px, env(safe-area-inset-top));
    padding-bottom: max(64px, calc(env(safe-area-inset-bottom) + 32px));
  }
  @media (max-width: 480px) {
    .wrap {
      padding-left: max(14px, env(safe-area-inset-left));
      padding-right: max(14px, env(safe-area-inset-right));
      padding-top: max(20px, env(safe-area-inset-top));
    }
  }
  .install-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  #ios-hint { font-size: 12.5px; }
  button { -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
</style>
"""

INSTALL_UI = """  <footer>
    <div class="install-row">
      <button id="install" class="primary" type="button" hidden>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        Install app
      </button>
      <span id="ios-hint" hidden>To install: tap the Share button, then <strong>Add to Home Screen</strong>.</span>
    </div>
"""

BOOT = """
<script>
(function () {
  "use strict";
  // ---- install prompt (Android / desktop Chrome) ----
  var installBtn = document.getElementById("install");
  var deferred = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    installBtn.hidden = false;
  });
  installBtn.onclick = function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.then(function () {
      deferred = null;
      installBtn.hidden = true;
    });
  };
  window.addEventListener("appinstalled", function () {
    installBtn.hidden = true;
    deferred = null;
  });

  // ---- iOS has no install prompt; point at the Share sheet instead ----
  var standalone = false;
  try {
    standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  } catch (e) {}
  var iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
            (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (iOS && !standalone) document.getElementById("ios-hint").hidden = false;

  // ---- offline shell ----
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./sw.js").catch(function () {});
    });
  }
})();
</script>
"""


def fail(msg):
    sys.exit(f"build-pwa: {msg}")


def main():
    if not SRC.exists():
        fail(f"missing {SRC.relative_to(ROOT)}")
    if not LIB.exists():
        fail(f"missing {LIB.relative_to(ROOT)}")

    html = SRC.read_text(encoding="utf-8")
    lib = LIB.read_text(encoding="utf-8")

    if "</script" in lib:
        fail("vendored library contains '</script' and cannot be inlined verbatim")

    # 1. Inline the library ahead of the app script, so the app owes the
    #    network nothing. The page's lazy loader finds window.ZXing already
    #    defined and resolves without ever issuing a request.
    if html.count(APP_SCRIPT) != 1:
        fail(f"expected exactly 1 app <script> in web/reticle.html, found {html.count(APP_SCRIPT)}")
    html = html.replace(
        APP_SCRIPT,
        "<script>\n" + lib.strip() + "\n</script>\n\n" + APP_SCRIPT,
        1,
    )

    # 2. PWA head tags.
    if "</head>" not in html:
        fail("no </head> in web/reticle.html")
    html = html.replace("</head>", PWA_HEAD + "</head>", 1)

    # 3. Install affordances + boot script.
    if "  <footer>\n" not in html:
        fail("no footer in web/reticle.html")
    html = html.replace("  <footer>\n", INSTALL_UI, 1)

    if "</body>" not in html:
        fail("no </body> in web/reticle.html")
    html = html.replace("</body>", BOOT + "</body>", 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB, decoder inlined)")


if __name__ == "__main__":
    main()
