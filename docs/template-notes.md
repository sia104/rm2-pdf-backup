# Template notes

Template support is required for DIAD beamline forms.

Current stage:

- copy and inventory the RM2 template directory;
- parse copied `templates.json` template metadata;
- record copied template file counts in run reports;
- detect template references in document content where possible;
- resolve template references through `templates.json` aliases and file stems;
- prefer SVG template assets and fall back to PNG when needed;
- treat missing template backgrounds as warnings, not publication blockers.

Chosen policy:

- exported PDFs should include templates;
- if a template is missing, publish handwriting and warn;
- run reports should note `template_background=svg`, `template_background=png`, or `template_background=omitted` when template rendering is attempted;
- custom templates should be supported;
- existing successful PDFs should not be regenerated just because a template changes later;
- exact visual matching is the long-term target;
- automated visual checks are future work.
