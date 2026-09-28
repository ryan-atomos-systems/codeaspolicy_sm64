# SM64 Policy Lab project page

A static research project page adapted from the Nerfies template, following the
demo / method / experiments structure used by Code as Policies and Eureka.
The copy is written as a short project report; the longer technical account
remains in `docs/publication/paper.tex`.

## Build and preview

From the repository root, with the verified recording present:

```sh
python3 scripts/build_website.py
python3 scripts/preview_website.py
```

Open http://127.0.0.1:8770/. Python needs no third-party packages. FFmpeg is needed
for the first video encode (`brew install ffmpeg` on the development Mac).
Later exports reuse the encoded video if the recording identity has not changed.
The preview server binds only to loopback and supports HTTP byte ranges for
video chapter seeking. Python's basic `http.server` does not reliably support
seeking in browsers before the entire video is buffered. GitHub Pages handles
static hosting; the Python helper is only for local preview.

The output is self-contained: HTML, CSS, JavaScript, a complete MP4, a bounded
decision excerpt and its images, the vendored 3D viewer, selected Python source,
paper source, and evidence notes. It contains no ROM, extracted assets, engine
binary, save directory, or full oracle trace. Raw experiments and the generated
export stay in ignored `artifacts/` in this repository.

## GitHub Pages

The script creates both `artifacts/project-site/` and
`artifacts/project-site-github-pages.zip`. The latter includes a manual deployment
workflow and `.nojekyll`.

1. Copy the exported folder's contents (including hidden files) into a separate
   GitHub Pages repository you own. The source repository is
   `ryan-atomos-systems/codeaspolicy_sm64`; keep this generated export separate
   from the source checkout's root.
2. Under **Settings → Pages**, choose **GitHub Actions**.
3. Run **Actions → Deploy project page → Run workflow**.

Alternatively choose **Deploy from a branch**, `main`, and `/(root)`; the site
needs no build on GitHub. Relative links support both repository subpaths and
custom domains. The generated README repeats these instructions. No deployment
has been performed as part of preparing the site.

See [GitHub's workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
The export's workflow is inert until it is placed in a publication repository
and manually run.

## Editing and validation

- Edit `index.html`, `style.css`, and `site.js` here, then rebuild.
- The maintained 3D implementation is copied from the existing dashboard, so
  fixes there propagate on export. Browser data uses the same input / action /
  outcome timing as the dashboard. The excerpt spans outcomes 1437–1491.
- The full video preserves order at 10 recorded images/s. Its final endpoint is
  quantized to that cadence; the authoritative collection times come from state.
- Keep visible labels for oracle access, the native port, skipped intro, and
  human direction. Do not turn matching traces into a general success-rate claim.
- Run `node --check website/site.js` and check the built page in a browser. Verify
  chapter seeking, speed selection, decision stepping, object inspection,
  input/outcome switching, small-screen layout, and the no-WebGL fallback.
- Preserve the template attribution in the footer and [LICENSE.md](LICENSE.md).

The static page never executes policy code or talks to the local dashboard API.
It fetches only its own packaged assets. No CDN, analytics, or remote font is used.
