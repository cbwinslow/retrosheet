# Issue 5: Documentation & Issue Linking Policy

**Purpose**: Establish a project‑wide standard for how GitHub issues are documented, updated, and cross‑referenced. This ensures that every piece of work is traceable, reproducible, and linked to the relevant code, SQL migrations, and design documents.

## Policy Summary (mirrored in `AGENTS.md`)
- **Comprehensive Updates**: Each issue must contain a detailed comment thread that records the rationale, implementation details, decisions made, and any open questions.
- **Markdown Links**: Include links to all related artifacts using markdown syntax, e.g., `[AGENTS.md](../AGENTS.md)`, `[sql/050_feature_marts.sql](../sql/050_feature_marts.sql)`, `[docs/agents/PROJECT_OBJECTIVES.md](../docs/agents/PROJECT_OBJECTIVES.md)`.
- **Cross‑Reference**: When an issue resolves or depends on another, reference the related issue number (e.g., `#42`) and add a comment linking back.
- **Sub‑issues**: For large tasks, create sub‑issues and link them in the parent issue description and comments.
- **Review Cycle**: Before closing, ensure the issue thread fully captures the work performed and all relevant artifacts are linked.
- **Automation**: Use the repository's issue templates to enforce these fields where possible.

## Implementation Steps
1. **Create Issue Template**: Add a template under `.github/ISSUE_TEMPLATE/` that includes sections for *Links*, *Progress Updates*, and *Related Issues*.
2. **Update Existing Issues**: Edit open issues to include the required sections and links to relevant docs.
3. **Enforce via CI (optional)**: Add a lightweight CI check that validates the presence of markdown links in issue bodies.
4. **Reference in `AGENTS.md`**: The policy is documented in `AGENTS.md` under the *Documentation & Issue Linking Policy* section. See line 146‑158.

## References
- `AGENTS.md` – Updated policy section.
- `docs/agents/PROCEDURES.md` – Workflow for issue creation and updates.
- `github_issues/issue_01_core_llm_integration.md` – Example of a detailed issue following this policy.

---

*Please ensure that any new issue created from now on follows this policy. Add a comment linking back to this issue when the policy is applied.*

