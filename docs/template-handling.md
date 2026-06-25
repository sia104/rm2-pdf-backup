# Template handling policy

DIAD form templates are part of the scientific/operational record and should be rendered in exported PDFs.

Current policy:

- copied standard and custom templates are inventoried from `raw/current/templates`;
- document `.content` files are scanned for referenced template names/IDs where possible;
- run reports record template file counts, `templates.json` availability, referenced templates and missing references;
- missing template backgrounds do not block publication;
- handwriting-only PDFs may be published with a clear template warning;
- historical PDFs are treated as historical artifacts and are not regenerated merely because a template changes.

Future work:

- confirm whether the selected renderer includes templates by default;
- if needed, add an exact template composition layer;
- add automated visual validation against known template reference images.
