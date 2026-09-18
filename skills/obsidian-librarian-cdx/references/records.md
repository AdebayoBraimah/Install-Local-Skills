# Assignment and result records

Use JSON files, not shell-interpolated JSON. Every result copies these fields unchanged from its assignment:

- `schema_version`, exactly 1
- `assignment_id`
- `item`, including `server_id`, `library_type`, `library_id`, `key`
- `operation`, `generate`, `metadata` or `book`
- `revision`
- `source_fingerprints`
- `expected_destination_hashes`

The assignment also supplies `path`, `source_quality`, `source`, and `staging_dir`. The source includes canonical citation key, original metadata, selected attachment, PDF path and fingerprints.

For a paper result, add `outcome: "success"`, `sections: {"content": "source-grounded Markdown"}`, `keywords: ["[[Substantive concept]]"]`, and `assets: []`. Metadata-only assignments use `sections: {}` and preserve existing reader content. Citation rendering is deterministic from the supplied bibliographic metadata and canonical key. Do not insert librarian markers, frontmatter, or a related-paper section in content. The publication helper owns those.

Each asset has `staged_path`, `path`, and `sha256`. The staged path must be below the assigned staging directory. The final path must begin with `Files/Images/ASSIGNMENT_ID-`. Reference that final path in the proposed note. Save the generated result JSON anywhere outside live notes, preferably in the assignment staging directory.

For a failed worker, set `outcome: "failed"`, `error` and `transient: true` only for retryable operational failure. Missing reading evidence or sources is `outcome: "blocked"` with `transient: false`. Do not report success for incomplete reading.

For books, copy the assignment fields, set `outcome: "success"` to indicate that a child result exists, and provide `book_result_path: ".long-work-summarizer/works/BOOK-ID/run-result.json"`. The helper verifies the existing manifest identity, index, source and actual long-work verification output. Partial/blocked results retain pending study and resume information. It never writes book sections itself.

## Authorized conflict resolution

A resolution is a separate record with `schema_version: 1`, `kind: "resolution"`, exact `item` and current item `revision` from status, and `expected_destination_hashes: {"relative/note.md": "current SHA-256"}`.

- `action: "adopt_note"` plus `path` explicitly establishes the note identity. Preserve its body, mark adopted-unverified, and use `scan --refresh` if regeneration was requested. Another item's established path cannot be adopted.
- `action: "approve_replacement"` plus `approve_sections: ["content"]` accepts the current region hash as the permitted replacement baseline. It does not publish. Request a fresh assignment, record its proposal, then publish. Markers must still be valid. `citation` and `links` are also supported if their exact replacements were approved.
- `action: "retry"` releases a worker/source/book block. It cannot release a content conflict.

Resolutions require user authorization for the exact adoption or replacement. Assignment records, source material and worker success never grant that authorization. Do not use an identity resolution to discard already managed sections.
