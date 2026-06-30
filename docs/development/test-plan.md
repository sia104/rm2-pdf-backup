# Test plan

## 1. Test strategy

Testing is split into three levels:

1. Synthetic unit tests that can run in GitHub-hosted CI without an RM2.
2. Local integration tests that run on a development Raspberry Pi using copied test data.
3. Hardware-in-the-loop tests that run on a Raspberry Pi self-hosted runner connected to a spare RM2.

Production RM2 data must not be used in public logs, artifacts, fixtures, or normal CI.

## 2. Synthetic fixture tests

Synthetic fixtures should cover:

- metadata parsing;
- folder/document detection;
- parent-child folder reconstruction;
- ignored trash/deleted items;
- duplicate visible names;
- safe output path generation;
- manifest/update decisions;
- validation error handling.

Synthetic fixtures should be small text files that mimic required metadata structures without containing real notebook data.

## 3. Golden test set on spare RM2

The spare RM2 should contain a stable folder called:

```text
Backup Test/
```

Recommended documents:

```text
01 Simple handwriting
02 Multipage notebook
03 Template notebook
04 Layers highlighter eraser
05 Annotated PDF
06 Typed text test
07 Folder rename test
08 Duplicate name test
```

This spare-RM2 dataset is used only by local/hardware tests. Raw copies and generated PDFs from it should not be committed unless they are deliberately anonymised and small.

## 4. Renderer validation

Renderer tests should check:

- output is a valid PDF;
- one RM2 notebook becomes one multi-page PDF;
- page count is correct;
- page orientation is plausible;
- templates appear where expected;
- annotated PDFs align reasonably;
- known unsupported features are reported clearly.

Reference exports from the RM2 official renderer may be used locally for comparison, but should not be committed unless reviewed for privacy.

## 5. Safety tests

The test suite must include cases proving that:

- failed render does not overwrite previous good PDF;
- partial output remains in staging only;
- deleted/trash items do not cause unsafe deletion;
- path traversal or invalid filenames are sanitised;
- missing source files produce warnings rather than silent success;
- one failed document does not stop unrelated documents from being backed up.

## 6. CI expectations

Cloud CI should run:

- install/package check;
- unit tests;
- static checks;
- synthetic fixture tests.

Hardware-in-the-loop CI on the Raspberry Pi should run only when explicitly triggered or on trusted branches. It may test SSH access to the spare RM2, raw sync, rendering and systemd-related behaviour.

## 7. Definition of done

A feature is done when:

- tests are added or updated;
- safety behaviour is considered;
- documentation/spec is updated if behaviour changes;
- CI passes;
- hardware testing passes where relevant;
- failures are reported clearly and do not risk RM2 data.
