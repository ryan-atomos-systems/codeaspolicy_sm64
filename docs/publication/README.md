# First Bowser publication drafts

Prepared September 28, 2026. These are local drafts; nothing has been published.

- [Paper](paper.tex): standalone LaTeX technical report, with an embedded bibliography and vector system diagram. Open in the Codex LaTeX editor for the PDF preview.
- [Project website](../../website/README.md): a GitHub Pages export using the Nerfies research-page template, with the full recording and an interactive 3D decision example.
- [Blog post](blog.md): the text edition, rewritten in the direct method/results style of the project page.
- [Tweets](tweets.md): a nine-post thread and three standalone alternatives. Each numbered draft fits 280 characters, including its numbering.
- [Evidence and editorial notes](evidence.md): claim-to-artifact mapping, timing conventions, publication assets, and reproducibility limitations.

The central claim is **eight unique stars and the first Bowser key in one continuous run from an empty save on castle grounds**. The development agent is **GPT-6 Astra**; the deployed policy is Python code consuming privileged game observations. The result uses a modified native PC port with the intro skipped. Full-game completion and vision-only control remain future work.

The paper compiles without external figures or a BibTeX file. Original experiment recordings remain in ignored `artifacts/`. The website exporter packages curated media into a self-contained site and ZIP in `artifacts/`, ready to copy into a publication repository. The exported site works without the local dashboard or game. Local dashboard links in the original evidence notes still require `make dashboard` and are not public share links.
