# Embedding the funding hub (Wix and elsewhere)

The public interface lives in `web/`. It is a static site with three files
(`index.html`, `styles.css`, `app.js`) and one **self-contained** build
(`web/wix-bundle.html`) that inlines the CSS and JS so it has **no external
dependencies**.

GitHub Pages serves the multi-file site at:
`https://phirilab.github.io/global-funding-intelligence/`

## Recommended: embed by URL (iframe)

In the Wix editor: **Add → Embed Code → Embed a Site** (an iframe element),
set the URL to the GitHub Pages address above, make it full width, give it a
tall or "adjust height to content" setting, and allow scrolling.

## Alternative: paste the self-contained bundle

Use **Add → Embed Code → Custom Embed → Code**, and paste the entire contents of
`web/wix-bundle.html`. Because that file inlines everything, nothing has to be
fetched cross-origin, so filters, search, the details modal, theme toggle and
in-page navigation all work inside the Wix iframe. In-page section links use a
JavaScript smooth-scroll handler so they work inside an embed, where native
`#anchor` scrolling is unreliable.

## Do NOT do these (they are the usual "the page shows but clicks do nothing")

- **Do not load `app.js`/`styles.css` from `raw.githubusercontent.com`.** GitHub
  raw serves them as `text/plain` with `X-Content-Type-Options: nosniff`, so the
  browser refuses to execute the script — every button, filter and nav link goes
  dead. Serve from GitHub Pages (correct MIME types) or use the inlined bundle.
- **Do not inject the full page through Wix "Custom Code → Body: End".** That
  drops a whole HTML document into your Wix page: the global CSS leaks onto your
  Wix theme and relative script paths 404. Use an iframe embed instead.

## Updating

Edit the source files in `web/`, then rebuild the bundle so it stays in sync:

```
cd web && node -e "const fs=require('fs');let h=fs.readFileSync('index.html','utf8');h=h.replace(/\s*<link rel=\"preconnect\"[^>]*>/g,'').replace(/\s*<link href=\"https:\/\/fonts\.googleapis\.com[^>]*>/g,'').replace(/\s*<link rel=\"stylesheet\" href=\"styles\.css\"\s*\/>/,'\n  <style>'+fs.readFileSync('styles.css','utf8')+'</style>').replace(/\s*<script src=\"app\.js\"><\/script>/,'\n  <script>'+fs.readFileSync('app.js','utf8')+'</script>');fs.writeFileSync('wix-bundle.html',h);"
```
