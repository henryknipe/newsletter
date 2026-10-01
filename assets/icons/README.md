# Update icons

Drop PNG icons here (e.g. downloaded from https://www.magnific.com/icons) and
reference them from an issue's `content.yaml`:

```yaml
updates:
  - title: Moderation queue
    icon: assets/icons/queue.png
```

- Use PNG, square, at least 96x96 px (displayed at 48 px, so 2x for retina).
- Local icons are embedded in `newsletter.eml` as inline attachments. In
  `newsletter.html` they are only local file paths, so if you paste that HTML
  somewhere else, upload the icon and use its URL (`icon: https://...`).
- Check the icon licence. Free icons from Magnific/Freepik usually need an attribution.

With no `icon:`, updates alternate between the two icons from the original Postcards template.
