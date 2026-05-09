# Recommendations Log (UTC)

## Task Revisit Snapshot (from local roadmap docs)
Based on `v2_0_ROADMAP.md`, high-priority open/incomplete items to tackle next:
1. #119 CLI modularization (defer non-core command imports to runtime).
2. #121 production database bootstrap infra (idempotent SQL + bootstrap command verification).
3. #122 advanced PostgreSQL features (materialized views, procedures, function library for low-latency modeling).

## Concrete Next Steps
1. Add a `baseball doctor` command for dependency diagnostics and actionable install guidance.
2. Add `baseball bootstrap <source>` integration tests with mock DB + mock source adapters.
3. Split optional subsystems (chatbot, embeddings, UI) behind optional extras and lazy command registration.
4. Add universal test harness command:
   - structured stack traces
   - failed-test artifact capture
   - environment fingerprinting
5. Add DB migration verification checks:
   - schema existence
   - table grains/PK/FK compliance
   - index health and query plan smoke checks.
