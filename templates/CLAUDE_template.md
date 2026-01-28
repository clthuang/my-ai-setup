# [Project Name]

[One sentence describing what this project does]

## Commands
```bash
dev       # Start dev server
build     # Build for production
test      # Run test suite
lint      # Run linter
typecheck # Type check (if applicable)
```

## Verify (IMPORTANT)
Before completing ANY code task, run:
```bash
[pkg] typecheck && [pkg] lint && [pkg] test
```
Iterate until all pass. Do not skip verification.

## Stack
- Language: [e.g., TypeScript 5.x]
- Framework: [e.g., Next.js 14]
- Database: [e.g., PostgreSQL 16]
- Package manager: [npm/pnpm/yarn/uv]

## Structure
```
src/
├── [dir]/   # [what it contains]
├── [dir]/   # [what it contains]
└── [dir]/   # [what it contains]
```

## Gotchas
- [Project-specific thing that causes problems]
- [Non-obvious behavior or requirement]

## Finding Info
- Architecture decisions: `docs/architecture.md`
- API patterns: `docs/api.md`
- For complex workflows, use Skills

---
<!-- 
╔══════════════════════════════════════════════════════════════════╗
║                    CLAUDE.MD DESIGN PRINCIPLES                   ║
║                  (Delete this section after setup)               ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🎯 CORE INSIGHT (Boris Cherny, Claude Code creator):            ║
║     "Give Claude a way to verify its work" → 2-3x quality        ║
║     Verification is THE most important section.                  ║
║                                                                  ║
║  📏 SIZE TARGET:                                                 ║
║     • Root CLAUDE.md: <60 lines, <500 lines absolute max         ║
║     • Anthropic's team: ~2.5k tokens                             ║
║     • HumanLayer: <60 lines                                      ║
║                                                                  ║
║  ✂️  THE PRUNING TEST (Anthropic official):                      ║
║     For each line ask: "Would removing this cause Claude         ║
║     to make mistakes?" If NO → delete it.                        ║
║     "Bloated CLAUDE.md files cause Claude to IGNORE              ║
║     your actual instructions!"                                   ║
║                                                                  ║
║  ❌ DO NOT INCLUDE (Claude already knows these):                 ║
║     • Generic principles (KISS, YAGNI, clean code)               ║
║     • Quality attributes (security, reliability)                 ║
║     • Communication style preferences                            ║
║     • Decision frameworks                                        ║
║     • Code style rules (use linters + hooks instead)             ║
║                                                                  ║
║  ✅ ONLY INCLUDE:                                                ║
║     • Verification commands (REQUIRED)                           ║
║     • Project-specific commands Claude can't infer               ║
║     • Gotchas specific to THIS project                           ║
║     • Where to find more info (progressive disclosure)           ║
║     • Stack info Claude can't detect                             ║
║                                                                  ║
║  📚 PROGRESSIVE DISCLOSURE:                                      ║
║     Don't dump everything here. Tell Claude WHERE to find        ║
║     info. Use Skills for domain-specific workflows.              ║
║                                                                  ║
║  🔄 ITERATION RULE (Boris Cherny):                               ║
║     "When Claude does something wrong, add a rule."              ║
║     Update multiple times per week. Check into git.              ║
║                                                                  ║
║  💡 EMPHASIS:                                                    ║
║     Use "IMPORTANT" or "REQUIRED" sparingly (2-3 rules max)      ║
║     to improve adherence on critical items.                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
-->