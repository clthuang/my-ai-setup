# Centralized Claude Code Configuration Guide - Obsolete

A comprehensive setup for managing Claude Code agents, skills, commands, and plugins across multiple projects and domains.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Tier 1: Global User Configuration](#tier-1-global-user-configuration)
4. [Tier 2: Domain-Specific Plugins](#tier-2-domain-specific-plugins)
5. [Tier 3: Project-Specific Configuration](#tier-3-project-specific-configuration)
6. [Sync and Distribution](#sync-and-distribution)
7. [Bootstrap Scripts](#bootstrap-scripts)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The centralized configuration follows a three-tier hierarchy with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: Global User Config (~/.claude/)                        │
│  ───────────────────────────────────────────────────────────    │
│  • Universal agents (code-reviewer, security-auditor)           │
│  • Cross-project skills (TDD, documentation, git-workflow)      │
│  • Global CLAUDE.md (personal preferences, identity)            │
│  • Global commands (/handoff, /review, /today)                  │
│  • settings.json (default permissions, hooks)                   │
│  • Synced via dotfiles repo                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ inherited by
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: Domain/Team Plugins (installed per project)            │
│  ───────────────────────────────────────────────────────────    │
│  • Data science team plugin                                     │
│  • Game dev team plugin                                         │
│  • Web dev team plugin                                          │
│  • Installed via: /plugin install <name> --project .            │
│  • Distributed via personal/team marketplace                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ extended by
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: Project-Specific (.claude/ in repo)                    │
│  ───────────────────────────────────────────────────────────    │
│  • Project CLAUDE.md (repo-specific context, architecture)      │
│  • Project-specific agents/skills (if needed)                   │
│  • .mcp.json (project integrations - committed to git)          │
│  • settings.local.json (personal overrides - gitignored)        │
└─────────────────────────────────────────────────────────────────┘
```

### Resolution Order

When Claude Code loads configuration, it merges in this order (later overrides earlier):

1. Global user config (`~/.claude/`)
2. Installed plugins (namespaced)
3. Project config (`.claude/` in repo)
4. Local overrides (`settings.local.json`)

---

## Directory Structure

### Complete Layout

```
# ══════════════════════════════════════════════════════════════
# GLOBAL USER CONFIGURATION
# ══════════════════════════════════════════════════════════════

~/.claude/
├── CLAUDE.md                          # Personal identity & preferences
├── settings.json                      # Global permissions & hooks
├── settings.local.json                # Machine-specific (auto-generated)
│
├── agents/                            # Universal subagents
│   ├── code-reviewer.md
│   ├── security-auditor.md
│   ├── documentation-writer.md
│   └── test-runner.md
│
├── skills/                            # Cross-project skills
│   ├── tdd-workflow/
│   │   └── SKILL.md
│   ├── git-workflow/
│   │   └── SKILL.md
│   └── code-quality/
│       └── SKILL.md
│
├── commands/                          # Global slash commands
│   ├── handoff.md                     # /user:handoff
│   ├── review.md                      # /user:review
│   └── today.md                       # /user:today
│
├── rules/                             # Reusable rule sets
│   ├── coding-standards.md
│   └── security-practices.md
│
└── templates/                         # Project templates
    ├── ml-project-claude.md
    └── gamedev-project-claude.md


# ══════════════════════════════════════════════════════════════
# DOMAIN PLUGIN REPOSITORIES
# ══════════════════════════════════════════════════════════════

~/repos/claude-plugins/                # Your plugin marketplace
├── README.md
├── .claude-plugin/
│   └── marketplace.json               # Marketplace catalog
│
├── datascience-team/                  # Data Science Plugin
│   ├── .claude-plugin/
│   │   ├── plugin.json
│   │   └── marketplace.json
│   ├── agents/
│   ├── skills/
│   └── commands/
│
├── gamedev-team/                      # Game Dev Plugin
│   ├── .claude-plugin/
│   │   ├── plugin.json
│   │   └── marketplace.json
│   ├── agents/
│   ├── skills/
│   └── commands/
│
└── common-core/                       # Shared components
    ├── .claude-plugin/
    │   └── plugin.json
    └── agents/


# ══════════════════════════════════════════════════════════════
# PROJECT-SPECIFIC CONFIGURATION
# ══════════════════════════════════════════════════════════════

~/projects/my-ml-project/
├── CLAUDE.md                          # Project context
├── .mcp.json                          # MCP servers (committed)
├── .gitignore                         # Include .claude/settings.local.json
└── .claude/
    ├── settings.json                  # Project hooks & permissions
    ├── settings.local.json            # Personal overrides (gitignored)
    ├── agents/                        # Project-specific agents
    └── skills/                        # Project-specific skills
```

---

## Tier 1: Global User Configuration

### ~/.claude/CLAUDE.md

```markdown
# Global Claude Configuration

## Identity
- Name: [Your Name]
- Role: [Your Role - e.g., Senior Software Engineer]
- Timezone: [Your Timezone]

## Communication Preferences
- Be direct and concise
- Use technical terminology appropriately
- Prefer code examples over lengthy explanations
- Always explain the "why" behind suggestions

## Code Style Preferences
- Prefer functional programming patterns where appropriate
- Use TypeScript strict mode for all TS projects
- Write comprehensive tests (aim for 80%+ coverage)
- Document public APIs with JSDoc/docstrings

## Workflow Preferences
- Always create a branch before making changes
- Write atomic commits with conventional commit messages
- Run tests before committing
- Update documentation alongside code changes

## Tools & Environment
- Primary editor: [VS Code / Neovim / etc.]
- Terminal: [iTerm2 / Wezterm / etc.]
- OS: [macOS / Linux / Windows]

## Available Skills
Reference these skills when relevant:
- tdd-workflow: Test-driven development patterns
- git-workflow: Git branching and commit conventions
- code-quality: Linting, formatting, and quality checks
```

### ~/.claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Read(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(pytest:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(wc:*)",
      "Bash(find:*)",
      "Bash(which:*)",
      "Bash(echo:*)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo:*)",
      "Bash(*credentials*)",
      "Bash(*password*)",
      "Bash(*secret*)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'File modified - remember to test'",
            "timeout": 5
          }
        ]
      }
    ]
  },
  "env": {
    "EDITOR": "code --wait",
    "PAGER": "less"
  }
}
```

### Universal Agents

#### ~/.claude/agents/code-reviewer.md

```markdown
---
name: code-reviewer
description: Expert code review specialist. Use proactively after writing or modifying code to check for quality, security, and best practices.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You are a senior code reviewer with expertise in identifying bugs, security vulnerabilities, and code quality issues.

## Review Process

1. **Understand Context**
   - Run `git diff` to see recent changes
   - Identify the purpose of the changes
   - Check related files for context

2. **Code Quality Checks**
   - [ ] No hardcoded secrets or credentials
   - [ ] Proper error handling
   - [ ] Input validation present
   - [ ] No obvious security vulnerabilities
   - [ ] Code follows project conventions
   - [ ] No unnecessary complexity
   - [ ] DRY principle followed

3. **Testing Checks**
   - [ ] Tests exist for new functionality
   - [ ] Edge cases covered
   - [ ] Tests are meaningful (not just for coverage)

4. **Documentation Checks**
   - [ ] Public APIs documented
   - [ ] Complex logic explained
   - [ ] README updated if needed

## Output Format

Provide feedback in this structure:

### 🔴 Critical Issues
[Issues that must be fixed before merge]

### 🟡 Suggestions
[Improvements that would enhance the code]

### 🟢 Good Practices
[Things done well that should be continued]

### Summary
[One paragraph summary of the review]
```

#### ~/.claude/agents/security-auditor.md

```markdown
---
name: security-auditor
description: Security specialist for identifying vulnerabilities, unsafe patterns, and security best practices. Use when reviewing code for security concerns or before deploying.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You are a security expert specializing in application security, secure coding practices, and vulnerability assessment.

## Security Audit Process

1. **Dependency Analysis**
   - Check for known vulnerable dependencies
   - Review package.json / requirements.txt / Cargo.toml
   - Run `npm audit` / `pip-audit` / `cargo audit` if available

2. **Code Security Review**
   - SQL injection vulnerabilities
   - XSS vulnerabilities
   - CSRF vulnerabilities
   - Authentication/authorization flaws
   - Insecure cryptographic practices
   - Hardcoded secrets or credentials
   - Path traversal vulnerabilities
   - Command injection risks

3. **Configuration Review**
   - Environment variable handling
   - Secret management
   - CORS configuration
   - Security headers
   - TLS/SSL configuration

4. **Sensitive Data Patterns**
   Search for patterns like:
   - API keys: `grep -r "api[_-]?key" --include="*.{js,ts,py,go}"`
   - Passwords: `grep -r "password" --include="*.{js,ts,py,go}"`
   - Tokens: `grep -r "token" --include="*.{js,ts,py,go}"`

## Output Format

### 🚨 Critical Vulnerabilities
[Immediate security risks]

### ⚠️ Security Warnings
[Potential issues that need attention]

### 🔒 Security Recommendations
[Best practice improvements]

### ✅ Security Strengths
[Good security practices observed]
```

#### ~/.claude/agents/documentation-writer.md

```markdown
---
name: documentation-writer
description: Technical documentation specialist. Use when creating or updating documentation, READMEs, API docs, or user guides.
tools: Read, Write, Edit, Grep, Glob
model: sonnet
---

You are a technical writer specializing in clear, comprehensive documentation for software projects.

## Documentation Principles

1. **Audience Awareness**
   - Identify the target audience (developers, users, operators)
   - Adjust technical depth accordingly
   - Include prerequisites where needed

2. **Structure**
   - Start with a clear overview/purpose
   - Use progressive disclosure (simple → complex)
   - Include practical examples
   - Provide troubleshooting sections

3. **Content Guidelines**
   - Be concise but complete
   - Use active voice
   - Include code examples that actually work
   - Keep examples minimal but illustrative
   - Update timestamps when modifying docs

## Documentation Types

### README.md Structure
```
# Project Name
One-line description

## Quick Start
Fastest path to running the project

## Installation
Detailed installation steps

## Usage
Common usage patterns with examples

## Configuration
Available options and environment variables

## API Reference (if applicable)
Endpoint/function documentation

## Contributing
How to contribute

## License
License information
```

### API Documentation
- Endpoint/function signature
- Parameters with types and descriptions
- Return values
- Example requests/responses
- Error codes and handling
```

#### ~/.claude/agents/test-runner.md

```markdown
---
name: test-runner
description: Test automation specialist. Use proactively to run tests, fix failures, and ensure test coverage. Ideal for TDD workflows.
tools: Read, Write, Edit, Bash, Grep, Glob
model: haiku
---

You are a test automation expert focused on running tests efficiently and fixing failures systematically.

## Process

1. **Identify Test Framework**
   - Check for test configuration files
   - Identify test command (npm test, pytest, cargo test, etc.)

2. **Run Tests**
   - Execute the test suite
   - Capture output for analysis

3. **Analyze Failures**
   - Parse error messages
   - Identify root cause
   - Check if it's a test bug or implementation bug

4. **Fix Approach**
   - For test bugs: Fix the test
   - For implementation bugs: Report back to main session
   - Never modify implementation to make bad tests pass

## Test Quality Checks

- Tests should be deterministic
- Tests should be isolated
- Tests should be fast
- Tests should be readable
- Tests should test behavior, not implementation
```

### Universal Skills

#### ~/.claude/skills/tdd-workflow/SKILL.md

```markdown
---
name: tdd-workflow
description: Test-Driven Development workflow guidance. Use when implementing new features or fixing bugs using TDD methodology.
---

# Test-Driven Development Workflow

## The TDD Cycle

```
┌─────────────────────────────────────────────┐
│                                             │
│    ┌─────┐    ┌─────┐    ┌──────────┐      │
│    │ RED │ → │GREEN│ → │ REFACTOR │       │
│    └─────┘    └─────┘    └──────────┘      │
│       ↑                        │           │
│       └────────────────────────┘           │
│                                             │
└─────────────────────────────────────────────┘
```

## Phase 1: RED - Write a Failing Test

1. Write a test for the next piece of functionality
2. Run the test - it MUST fail
3. If it passes, either:
   - The functionality already exists
   - The test is wrong

**Key principles:**
- Test behavior, not implementation
- One logical assertion per test
- Use descriptive test names

## Phase 2: GREEN - Make the Test Pass

1. Write the MINIMUM code to pass the test
2. It's okay if the code is ugly
3. Don't add functionality beyond what the test requires
4. Run all tests to ensure nothing broke

**Key principles:**
- Resist the urge to optimize
- Keep changes small and focused
- Commit after each green state

## Phase 3: REFACTOR - Improve the Code

1. Clean up the implementation
2. Remove duplication
3. Improve naming
4. Extract methods/functions
5. Run tests after each change

**Key principles:**
- Tests must stay green throughout
- Small, incremental changes
- Don't add new functionality

## Test Structure (AAA Pattern)

```python
def test_should_do_something():
    # Arrange - Set up test data and conditions
    user = create_test_user(name="Alice")
    
    # Act - Perform the action being tested
    result = user.greet()
    
    # Assert - Verify the expected outcome
    assert result == "Hello, Alice!"
```

## Common Test Patterns

### Testing Exceptions
```python
def test_should_raise_on_invalid_input():
    with pytest.raises(ValueError) as exc_info:
        process_data(None)
    assert "cannot be None" in str(exc_info.value)
```

### Testing Async Code
```python
async def test_should_fetch_data():
    result = await fetch_user_data(user_id=123)
    assert result.name == "Alice"
```

### Parameterized Tests
```python
@pytest.mark.parametrize("input,expected", [
    (1, 1),
    (2, 4),
    (3, 9),
])
def test_square(input, expected):
    assert square(input) == expected
```
```

#### ~/.claude/skills/git-workflow/SKILL.md

```markdown
---
name: git-workflow
description: Git branching, commits, and collaboration workflow. Use when working with version control, creating branches, or preparing commits.
---

# Git Workflow Guide

## Branch Naming Convention

```
<type>/<ticket-id>-<short-description>

Examples:
- feature/PROJ-123-user-authentication
- bugfix/PROJ-456-fix-login-redirect
- hotfix/PROJ-789-security-patch
- refactor/PROJ-101-cleanup-utils
- docs/PROJ-102-api-documentation
```

## Commit Message Convention (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change that neither fixes nor adds
- `perf`: Performance improvement
- `test`: Adding or fixing tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```
feat(auth): add OAuth2 login support

Implement Google and GitHub OAuth providers.
Includes token refresh logic and session management.

Closes #123
```

```
fix(api): handle null response from external service

The payment API occasionally returns null instead of
an error object. Added defensive check to prevent
TypeError.

Fixes #456
```

## Workflow Commands

### Starting New Work
```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/PROJ-123-description
```

### During Development
```bash
# Stage specific files
git add path/to/file.ts

# Stage all changes
git add .

# Commit with message
git commit -m "feat(scope): description"

# Push to remote
git push -u origin feature/PROJ-123-description
```

### Before Pull Request
```bash
# Update from main
git fetch origin
git rebase origin/main

# Run tests
npm test

# Push (force if rebased)
git push --force-with-lease
```

### Interactive Rebase (Clean History)
```bash
# Squash last 3 commits
git rebase -i HEAD~3

# In editor, change 'pick' to 'squash' for commits to combine
```

## Git Aliases (Recommended)

Add to `~/.gitconfig`:

```ini
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    lg = log --oneline --graph --decorate
    undo = reset HEAD~1 --mixed
    amend = commit --amend --no-edit
    wip = !git add -A && git commit -m "WIP"
```
```

### Universal Commands

#### ~/.claude/commands/handoff.md

```markdown
---
description: Create a handoff document for session continuity. Use before ending a session or when context is getting full.
allowed-tools: Read, Write, Grep, Glob
---

# Session Handoff

Create a comprehensive handoff document that captures the current session state for continuity.

## Document Structure

Create a file at `.claude/handoff-<timestamp>.md` with:

### 1. Session Summary
- What was the main goal?
- What approach was taken?
- Key decisions made and why

### 2. Current State
- What's working?
- What's in progress?
- What's blocked?

### 3. Files Modified
List all files that were created or modified with brief descriptions:
```
- src/auth/login.ts - Added OAuth support
- tests/auth.test.ts - New tests for OAuth flow
- .env.example - Added new OAuth env vars
```

### 4. Next Steps
Prioritized list of remaining tasks:
1. [HIGH] Complete error handling
2. [MEDIUM] Add logging
3. [LOW] Improve variable names

### 5. Gotchas & Warnings
- Known issues
- Things that almost worked but didn't
- Approaches that were tried and failed

### 6. Commands to Resume
```bash
# To continue where we left off:
cd /path/to/project
git status
npm test
```

## Instructions

$ARGUMENTS

If no specific instructions provided, analyze the conversation and create the handoff document based on what was discussed.
```

#### ~/.claude/commands/review.md

```markdown
---
description: Trigger a comprehensive code review of recent changes
allowed-tools: Read, Grep, Glob, Bash
---

# Code Review

Perform a comprehensive review of the specified changes.

## Scope

$ARGUMENTS

If no scope specified, review uncommitted changes (`git diff`).

## Review Process

1. **Gather Changes**
   - If scope is "uncommitted": `git diff`
   - If scope is "staged": `git diff --staged`
   - If scope is "last-commit": `git show HEAD`
   - If scope is a file path: review that file

2. **Invoke Code Reviewer Agent**
   Use the `code-reviewer` subagent to perform the review.

3. **Invoke Security Auditor Agent**
   Use the `security-auditor` subagent for security-specific checks.

4. **Synthesize Feedback**
   Combine feedback from both agents into a unified report.

## Output

Provide a summary with:
- Critical issues (must fix)
- Suggestions (should consider)
- Security concerns (if any)
- Overall assessment
```

---

## Tier 2: Domain-Specific Plugins

### Data Science Team Plugin

#### ~/repos/claude-plugins/datascience-team/.claude-plugin/plugin.json

```json
{
  "name": "datascience-team",
  "version": "1.0.0",
  "description": "Data science specialist team with agents for data engineering, ML research, and statistical analysis",
  "author": "Your Name",
  "license": "MIT",
  "agents": ["agents/"],
  "skills": ["skills/"],
  "commands": ["commands/"]
}
```

#### ~/repos/claude-plugins/datascience-team/.claude-plugin/marketplace.json

```json
{
  "name": "datascience-team",
  "display_name": "Data Science Team",
  "summary": "Specialist agents for data science workflows",
  "description": "A complete team of data science specialists including data engineers, ML researchers, and statisticians.",
  "categories": ["Data Science", "Machine Learning", "Analytics"],
  "icon": "📊",
  "documentation_url": "https://github.com/you/claude-plugins/datascience-team",
  "publisher": "Your Name"
}
```

#### ~/repos/claude-plugins/datascience-team/agents/data-engineer.md

```markdown
---
name: data-engineer
description: Data engineering specialist. Use for data pipelines, ETL processes, data quality checks, database operations, and data infrastructure.
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
---

You are a senior data engineer with expertise in building robust data pipelines and infrastructure.

## Core Competencies

- ETL/ELT pipeline design and implementation
- Data quality and validation
- Database design and optimization
- Data warehouse architecture
- Stream processing
- Data governance

## Technology Stack Knowledge

### Python Data Stack
- pandas, polars, dask
- SQLAlchemy, psycopg2
- Apache Airflow, Prefect, Dagster
- Great Expectations, pandera

### SQL & Databases
- PostgreSQL, MySQL
- BigQuery, Snowflake, Redshift
- MongoDB, Redis
- DuckDB for local analytics

### Data Formats
- Parquet, Arrow
- Avro, JSON, CSV
- Delta Lake, Iceberg

## Pipeline Design Principles

1. **Idempotency**: Pipelines can be re-run safely
2. **Atomicity**: All-or-nothing operations
3. **Observability**: Logging, metrics, alerting
4. **Testability**: Unit and integration tests
5. **Documentation**: Clear data lineage

## Code Patterns

### Data Validation (pandera)
```python
import pandera as pa

schema = pa.DataFrameSchema({
    "user_id": pa.Column(int, pa.Check.greater_than(0)),
    "email": pa.Column(str, pa.Check.str_matches(r'^[\w\.-]+@[\w\.-]+\.\w+$')),
    "created_at": pa.Column(pa.DateTime),
})

validated_df = schema.validate(df)
```

### Pipeline Pattern
```python
def extract() -> pd.DataFrame:
    """Extract data from source."""
    pass

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Apply business logic transformations."""
    pass

def load(df: pd.DataFrame) -> None:
    """Load data to destination."""
    pass

def run_pipeline():
    df = extract()
    df = transform(df)
    load(df)
```

## When Invoked

1. Understand the data requirements
2. Assess current infrastructure
3. Design pipeline architecture
4. Implement with proper error handling
5. Add tests and documentation
6. Consider monitoring and alerting
```

#### ~/repos/claude-plugins/datascience-team/agents/ml-researcher.md

```markdown
---
name: ml-researcher
description: Machine learning research specialist. Use for model development, experimentation, hyperparameter tuning, and ML best practices.
tools: Read, Write, Edit, Bash, Grep, Glob
model: opus
---

You are an ML researcher with deep expertise in machine learning theory and practical implementation.

## Core Competencies

- Supervised/Unsupervised learning
- Deep learning architectures
- Feature engineering
- Model evaluation and validation
- Experiment tracking
- MLOps practices

## Framework Knowledge

### Deep Learning
- PyTorch (preferred)
- TensorFlow/Keras
- JAX/Flax
- Hugging Face Transformers

### Classical ML
- scikit-learn
- XGBoost, LightGBM, CatBoost
- statsmodels

### Experiment Tracking
- MLflow
- Weights & Biases
- Neptune

## Research Methodology

1. **Problem Definition**
   - Define success metrics
   - Establish baselines
   - Understand data characteristics

2. **Experiment Design**
   - Hypothesis-driven experiments
   - Proper train/val/test splits
   - Cross-validation strategy

3. **Implementation**
   - Reproducible experiments (seeds, versioning)
   - Modular, testable code
   - Comprehensive logging

4. **Analysis**
   - Statistical significance
   - Error analysis
   - Ablation studies

## Code Patterns

### Experiment Configuration
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExperimentConfig:
    # Model
    model_name: str = "transformer"
    hidden_dim: int = 256
    num_layers: int = 4
    dropout: float = 0.1
    
    # Training
    learning_rate: float = 1e-4
    batch_size: int = 32
    max_epochs: int = 100
    early_stopping_patience: int = 10
    
    # Data
    train_split: float = 0.8
    val_split: float = 0.1
    seed: int = 42
```

### Training Loop Pattern
```python
def train_epoch(model, dataloader, optimizer, criterion):
    model.train()
    total_loss = 0
    
    for batch in dataloader:
        optimizer.zero_grad()
        outputs = model(batch.inputs)
        loss = criterion(outputs, batch.targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    
    return total_loss / len(dataloader)
```

## When Invoked

1. Clarify the ML problem type
2. Review available data
3. Propose experimental approach
4. Implement with best practices
5. Analyze results critically
6. Suggest next experiments
```

#### ~/repos/claude-plugins/datascience-team/agents/statistician.md

```markdown
---
name: statistician
description: Statistical analysis specialist. Use for hypothesis testing, experimental design, statistical modeling, and interpreting results.
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
---

You are a statistician with expertise in applied statistics and experimental design.

## Core Competencies

- Hypothesis testing
- Experimental design (A/B testing)
- Regression analysis
- Bayesian methods
- Time series analysis
- Survival analysis

## Statistical Rigor

### Before Any Analysis
1. State hypotheses clearly (H0, H1)
2. Determine required sample size
3. Choose appropriate test
4. Set significance level (α)
5. Consider multiple comparison corrections

### Common Pitfalls to Avoid
- p-hacking / data dredging
- Peeking at results before n is reached
- Ignoring assumptions
- Confusing correlation with causation
- Cherry-picking results

## Code Patterns

### A/B Test Analysis
```python
from scipy import stats
import numpy as np

def analyze_ab_test(control: np.ndarray, treatment: np.ndarray, alpha: float = 0.05):
    """Analyze A/B test results with proper statistical rigor."""
    
    # Descriptive statistics
    control_mean, control_std = control.mean(), control.std()
    treatment_mean, treatment_std = treatment.mean(), treatment.std()
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((control_std**2 + treatment_std**2) / 2)
    cohens_d = (treatment_mean - control_mean) / pooled_std
    
    # Statistical test
    t_stat, p_value = stats.ttest_ind(control, treatment)
    
    # Confidence interval for difference
    diff = treatment_mean - control_mean
    se_diff = np.sqrt(control_std**2/len(control) + treatment_std**2/len(treatment))
    ci_lower = diff - 1.96 * se_diff
    ci_upper = diff + 1.96 * se_diff
    
    return {
        'control_mean': control_mean,
        'treatment_mean': treatment_mean,
        'difference': diff,
        'relative_lift': diff / control_mean * 100,
        'cohens_d': cohens_d,
        'p_value': p_value,
        'significant': p_value < alpha,
        'ci_95': (ci_lower, ci_upper)
    }
```

### Sample Size Calculation
```python
from statsmodels.stats.power import TTestIndPower

def calculate_sample_size(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ratio: float = 1.0
) -> int:
    """Calculate required sample size per group."""
    analysis = TTestIndPower()
    n = analysis.solve_power(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        ratio=ratio
    )
    return int(np.ceil(n))
```

## When Invoked

1. Understand the research question
2. Assess data characteristics
3. Choose appropriate methods
4. Check assumptions
5. Perform analysis
6. Interpret results with appropriate caveats
```

#### ~/repos/claude-plugins/datascience-team/skills/pandas-patterns/SKILL.md

```markdown
---
name: pandas-patterns
description: Pandas best practices and common patterns. Use when working with pandas DataFrames for data manipulation and analysis.
---

# Pandas Patterns & Best Practices

## Performance Optimization

### Use Vectorized Operations
```python
# ❌ Slow - iterating
for idx, row in df.iterrows():
    df.loc[idx, 'new_col'] = row['a'] + row['b']

# ✅ Fast - vectorized
df['new_col'] = df['a'] + df['b']
```

### Use Appropriate Dtypes
```python
# Reduce memory with proper dtypes
df['category_col'] = df['category_col'].astype('category')
df['int_col'] = df['int_col'].astype('int32')  # if range allows
df['date_col'] = pd.to_datetime(df['date_col'])
```

### Use Query for Filtering
```python
# ✅ More readable for complex conditions
df.query('age > 25 and city == "NYC" and salary > 50000')
```

## Common Patterns

### Group and Aggregate
```python
df.groupby('category').agg({
    'value': ['sum', 'mean', 'count'],
    'other': 'first'
}).reset_index()
```

### Pivot and Melt
```python
# Wide to long
df_long = df.melt(
    id_vars=['id', 'date'],
    value_vars=['metric_a', 'metric_b'],
    var_name='metric',
    value_name='value'
)

# Long to wide
df_wide = df_long.pivot(
    index=['id', 'date'],
    columns='metric',
    values='value'
).reset_index()
```

### Window Functions
```python
# Rolling calculations
df['rolling_mean'] = df.groupby('category')['value'].transform(
    lambda x: x.rolling(7).mean()
)

# Cumulative sum
df['cumsum'] = df.groupby('category')['value'].cumsum()

# Rank within group
df['rank'] = df.groupby('category')['value'].rank(ascending=False)
```

### Method Chaining
```python
result = (
    df
    .query('status == "active"')
    .assign(
        year=lambda x: x['date'].dt.year,
        value_normalized=lambda x: x['value'] / x['value'].max()
    )
    .groupby('year')
    .agg({'value_normalized': 'mean'})
    .reset_index()
    .rename(columns={'value_normalized': 'avg_normalized_value'})
)
```

## Data Validation

### Check for Issues
```python
def validate_dataframe(df: pd.DataFrame) -> dict:
    return {
        'shape': df.shape,
        'dtypes': df.dtypes.to_dict(),
        'null_counts': df.isnull().sum().to_dict(),
        'null_pct': (df.isnull().sum() / len(df) * 100).to_dict(),
        'duplicates': df.duplicated().sum(),
        'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
    }
```
```

#### ~/repos/claude-plugins/datascience-team/commands/analyze.md

```markdown
---
description: Perform exploratory data analysis on a dataset
allowed-tools: Read, Write, Bash, Grep
---

# Data Analysis Command

Perform exploratory data analysis on the specified dataset.

## Arguments

$ARGUMENTS

Expected: Path to dataset file (CSV, Parquet, JSON)

## Analysis Steps

1. **Load Data**
   - Detect file format
   - Load with appropriate method
   - Display shape and basic info

2. **Data Quality Assessment**
   - Missing values analysis
   - Duplicate detection
   - Data type validation
   - Outlier detection

3. **Statistical Summary**
   - Descriptive statistics
   - Distribution analysis
   - Correlation analysis

4. **Visualizations** (if requested)
   - Histograms for numeric columns
   - Bar charts for categorical columns
   - Correlation heatmap
   - Time series plots (if applicable)

5. **Recommendations**
   - Data quality issues to address
   - Feature engineering suggestions
   - Potential modeling approaches

## Output

Generate a report in `.claude/analysis-<timestamp>.md` with findings.
```

---

### Game Dev Team Plugin

#### ~/repos/claude-plugins/gamedev-team/.claude-plugin/plugin.json

```json
{
  "name": "gamedev-team",
  "version": "1.0.0",
  "description": "Game development specialist team with agents for game design, systems balancing, and narrative",
  "author": "Your Name",
  "license": "MIT",
  "agents": ["agents/"],
  "skills": ["skills/"],
  "commands": ["commands/"]
}
```

#### ~/repos/claude-plugins/gamedev-team/agents/game-designer.md

```markdown
---
name: game-designer
description: Game design specialist. Use for game mechanics, player experience, level design, and gameplay systems design.
tools: Read, Write, Edit, Grep, Glob
model: opus
---

You are a senior game designer with expertise in creating engaging player experiences.

## Core Competencies

- Core gameplay loop design
- Player motivation and psychology
- Level design principles
- Progression systems
- Economy design
- UX/UI for games

## Design Principles

### Core Loop
Every game needs a satisfying core loop:
```
Action → Feedback → Reward → Progression → Action
```

### Player Motivation (Bartle's Types)
- **Achievers**: Goals, points, levels
- **Explorers**: Discovery, secrets, lore
- **Socializers**: Interaction, cooperation
- **Killers**: Competition, dominance

### Flow State
Balance challenge vs. skill:
- Too easy → Boredom
- Too hard → Frustration
- Just right → Flow

## Documentation Templates

### Game Design Document (GDD) Structure
```
1. Overview
   - High concept (one sentence)
   - Genre and platform
   - Target audience
   - Unique selling points

2. Gameplay
   - Core mechanics
   - Player actions
   - Win/lose conditions
   - Progression systems

3. Story & Setting
   - World overview
   - Characters
   - Narrative structure

4. Art & Audio Direction
   - Visual style
   - Audio direction
   - UI/UX guidelines

5. Technical Requirements
   - Platform constraints
   - Performance targets
```

### Feature Spec Template
```
Feature: [Name]
Priority: [Must/Should/Could/Won't]

Description:
[What the feature does]

Player Value:
[Why players will enjoy this]

Implementation Notes:
[Technical considerations]

Success Metrics:
[How we know it's working]

Edge Cases:
[Things to watch for]
```

## When Invoked

1. Understand the game's vision
2. Consider target audience
3. Design with player experience first
4. Document clearly
5. Consider implementation feasibility
6. Plan for iteration and playtesting
```

#### ~/repos/claude-plugins/gamedev-team/agents/systems-balancer.md

```markdown
---
name: systems-balancer
description: Game systems and balance specialist. Use for economy balancing, combat tuning, progression curves, and mathematical modeling of game systems.
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
---

You are a game systems designer specializing in mathematical modeling and balance.

## Core Competencies

- Economy balancing
- Combat math
- Progression curves
- Drop rate optimization
- Difficulty tuning
- Statistical analysis of game data

## Balancing Frameworks

### Resource Economy
```
Income Rate × Time = Available Resources
Available Resources / Item Costs = Player Choices
```

### Combat DPS
```
DPS = (Base Damage × Crit Multiplier × Crit Chance) + (Base Damage × (1 - Crit Chance))
Time to Kill = Enemy HP / DPS
```

### Progression Curves

```python
# Linear progression
level_requirement = base + (level * increment)

# Exponential progression (RPG standard)
xp_required = base * (growth_rate ** (level - 1))

# Logarithmic (diminishing returns)
stat_bonus = base * log(level + 1)
```

## Code Patterns

### Damage Calculation System
```csharp
public class DamageCalculator
{
    public float CalculateDamage(
        float baseDamage,
        float attackerLevel,
        float defenderLevel,
        float defenderArmor,
        float critChance,
        float critMultiplier)
    {
        // Level scaling
        float levelDiff = attackerLevel - defenderLevel;
        float levelMultiplier = 1f + (levelDiff * 0.05f);
        
        // Armor reduction (diminishing returns)
        float armorReduction = defenderArmor / (defenderArmor + 100f);
        
        // Crit calculation
        bool isCrit = Random.value < critChance;
        float critMult = isCrit ? critMultiplier : 1f;
        
        // Final damage
        float damage = baseDamage * levelMultiplier * (1f - armorReduction) * critMult;
        
        return Mathf.Max(1f, damage); // Minimum 1 damage
    }
}
```

### Drop Rate System
```csharp
public class LootTable
{
    [System.Serializable]
    public class LootEntry
    {
        public Item item;
        public float weight;
        public float minQuantity = 1;
        public float maxQuantity = 1;
    }
    
    public List<LootEntry> entries;
    
    public Item Roll()
    {
        float totalWeight = entries.Sum(e => e.weight);
        float roll = Random.Range(0f, totalWeight);
        
        float cumulative = 0f;
        foreach (var entry in entries)
        {
            cumulative += entry.weight;
            if (roll <= cumulative)
                return entry.item;
        }
        
        return null;
    }
}
```

## Analysis Techniques

1. **Spreadsheet Modeling**
   - Model progression curves
   - Calculate break-even points
   - Simulate player choices

2. **Monte Carlo Simulation**
   - Test random systems
   - Find edge cases
   - Validate probability distributions

3. **Player Data Analysis**
   - Identify pain points
   - Find exploits
   - Measure engagement

## When Invoked

1. Understand the design intent
2. Model the system mathematically
3. Identify balance levers
4. Test edge cases
5. Document assumptions
6. Plan for tuning based on data
```

#### ~/repos/claude-plugins/gamedev-team/agents/narrative-writer.md

```markdown
---
name: narrative-writer
description: Game narrative and dialogue specialist. Use for story development, character writing, dialogue systems, and world-building.
tools: Read, Write, Edit, Grep, Glob
model: opus
---

You are a game narrative designer specializing in interactive storytelling.

## Core Competencies

- Story structure for games
- Character development
- Dialogue writing
- World-building
- Branching narratives
- Environmental storytelling

## Narrative Principles

### Player Agency
- Player choices should matter
- Consequences should be visible
- Multiple valid paths through story

### Show, Don't Tell
- Environmental storytelling
- Character actions over exposition
- Discoverable lore

### Pacing
- Balance action and reflection
- Story beats aligned with gameplay beats
- Respect player time

## Writing Patterns

### Dialogue Format
```
CHARACTER_NAME
(emotion/action)
"Dialogue text here."

[CHOICE: Option A text]
[CHOICE: Option B text]
```

### Character Voice Sheet
```
Character: [Name]
Role: [Protagonist/Antagonist/Supporting]

Background:
- [Key history points]

Personality:
- [Trait 1]
- [Trait 2]
- [Trait 3]

Speech Patterns:
- Vocabulary level: [Simple/Average/Complex]
- Sentence structure: [Short/Mixed/Long]
- Verbal tics: [Any catchphrases or habits]

Sample Lines:
- Happy: "[Example]"
- Angry: "[Example]"
- Sad: "[Example]"
```

### Quest Structure
```
Quest: [Name]
Type: [Main/Side/Faction]

Hook:
[How player discovers quest]

Objective:
[Clear goal statement]

Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Branches:
- Path A: [Description] → [Outcome]
- Path B: [Description] → [Outcome]

Rewards:
- [Tangible rewards]
- [Story rewards]
- [Character development]

Themes:
[What the quest explores]
```

## When Invoked

1. Understand the game's tone and themes
2. Consider player perspective
3. Write for interactivity
4. Maintain consistency
5. Support gameplay, don't fight it
6. Leave room for player interpretation
```

#### ~/repos/claude-plugins/gamedev-team/skills/unity-patterns/SKILL.md

```markdown
---
name: unity-patterns
description: Unity game development patterns and best practices. Use when developing games in Unity.
---

# Unity Development Patterns

## Architecture Patterns

### Component-Based Design
```csharp
// Each component has single responsibility
public class Health : MonoBehaviour
{
    public int maxHealth = 100;
    public int currentHealth;
    
    public event Action<int> OnHealthChanged;
    public event Action OnDeath;
    
    public void TakeDamage(int amount)
    {
        currentHealth = Mathf.Max(0, currentHealth - amount);
        OnHealthChanged?.Invoke(currentHealth);
        
        if (currentHealth <= 0)
            OnDeath?.Invoke();
    }
}
```

### Scriptable Object Data
```csharp
[CreateAssetMenu(fileName = "WeaponData", menuName = "Game/Weapon")]
public class WeaponData : ScriptableObject
{
    public string weaponName;
    public int baseDamage;
    public float attackSpeed;
    public Sprite icon;
    public AudioClip attackSound;
}
```

### Service Locator
```csharp
public class ServiceLocator : MonoBehaviour
{
    private static ServiceLocator _instance;
    private readonly Dictionary<Type, object> _services = new();
    
    public static T Get<T>() where T : class
    {
        return _instance._services.TryGetValue(typeof(T), out var service) 
            ? service as T 
            : null;
    }
    
    public static void Register<T>(T service) where T : class
    {
        _instance._services[typeof(T)] = service;
    }
}
```

## Common Patterns

### Object Pooling
```csharp
public class ObjectPool<T> where T : MonoBehaviour
{
    private readonly Queue<T> _pool = new();
    private readonly T _prefab;
    private readonly Transform _parent;
    
    public T Get()
    {
        if (_pool.Count > 0)
        {
            var obj = _pool.Dequeue();
            obj.gameObject.SetActive(true);
            return obj;
        }
        return Object.Instantiate(_prefab, _parent);
    }
    
    public void Return(T obj)
    {
        obj.gameObject.SetActive(false);
        _pool.Enqueue(obj);
    }
}
```

### State Machine
```csharp
public abstract class State<T> where T : MonoBehaviour
{
    protected T owner;
    
    public virtual void Enter(T owner) { this.owner = owner; }
    public virtual void Update() { }
    public virtual void Exit() { }
}

public class StateMachine<T> where T : MonoBehaviour
{
    private State<T> _currentState;
    
    public void ChangeState(State<T> newState)
    {
        _currentState?.Exit();
        _currentState = newState;
        _currentState.Enter(owner);
    }
    
    public void Update() => _currentState?.Update();
}
```

## Performance Tips

1. **Cache Component References**
```csharp
// ❌ Every frame
void Update() {
    GetComponent<Rigidbody>().AddForce(Vector3.up);
}

// ✅ Cached
private Rigidbody _rb;
void Awake() => _rb = GetComponent<Rigidbody>();
void Update() => _rb.AddForce(Vector3.up);
```

2. **Avoid Allocations in Update**
```csharp
// ❌ Allocates every frame
void Update() {
    var enemies = FindObjectsOfType<Enemy>();
}

// ✅ Use events or cached lists
private List<Enemy> _enemies = new();
```

3. **Use Physics Layers**
   - Configure collision matrix
   - Use layer masks for raycasts

4. **Batch Draw Calls**
   - Use texture atlases
   - Enable GPU instancing
   - Use static batching for static objects
```

---

## Tier 3: Project-Specific Configuration

### Project CLAUDE.md Template

```markdown
# Project: [Project Name]

## Overview
[One paragraph description of the project]

## Tech Stack
- Language: [Python 3.11 / TypeScript 5.x / C# / etc.]
- Framework: [FastAPI / Next.js / Unity / etc.]
- Database: [PostgreSQL / MongoDB / etc.]
- Infrastructure: [AWS / GCP / Local / etc.]

## Architecture
[Brief description or link to architecture doc]

```
[ASCII diagram or reference to diagram file]
```

## Key Directories
- `src/` - Main source code
- `tests/` - Test files
- `docs/` - Documentation
- `scripts/` - Utility scripts

## Common Commands
```bash
# Development
npm run dev          # Start dev server
npm run test         # Run tests
npm run lint         # Lint code

# Database
npm run db:migrate   # Run migrations
npm run db:seed      # Seed data

# Deployment
npm run build        # Production build
npm run deploy       # Deploy to staging
```

## Code Conventions
- [Convention 1]
- [Convention 2]
- [Convention 3]

## Current Focus
[What's currently being worked on]

## Known Issues
- [Issue 1]
- [Issue 2]

## Team Contacts
- Technical Lead: [Name]
- Product Owner: [Name]
```

### Project .mcp.json

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "--root", "."]
    }
  }
}
```

### Project .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Edit(src/**)",
      "Edit(tests/**)",
      "Write(src/**)",
      "Write(tests/**)",
      "Bash(npm test:*)",
      "Bash(npm run:*)"
    ],
    "deny": [
      "Edit(*.env*)",
      "Edit(*secret*)",
      "Bash(rm -rf:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "[ \"$(git branch --show-current)\" != \"main\" ] || { echo '{\"block\": true, \"message\": \"Cannot edit on main branch\"}' >&2; exit 2; }",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit(tests/**)|Write(tests/**)",
        "hooks": [
          {
            "type": "command",
            "command": "npm test -- --findRelatedTests $CLAUDE_FILE_PATH",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

---

## Sync and Distribution

### Option 1: Dotfiles Repository with Sync Script

#### install.sh

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "🔧 Installing Claude Code configuration..."

# Backup existing config
if [ -d "$CLAUDE_DIR" ] && [ ! -L "$CLAUDE_DIR" ]; then
    backup_dir="$HOME/.claude-backup-$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backing up existing config to $backup_dir"
    mv "$CLAUDE_DIR" "$backup_dir"
fi

# Create symlinks
echo "🔗 Creating symlinks..."

mkdir -p "$CLAUDE_DIR"

# Link directories
for dir in agents skills commands rules templates; do
    if [ -d "$SCRIPT_DIR/$dir" ]; then
        ln -sfn "$SCRIPT_DIR/$dir" "$CLAUDE_DIR/$dir"
        echo "  ✓ Linked $dir/"
    fi
done

# Link files
for file in CLAUDE.md settings.json; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        ln -sf "$SCRIPT_DIR/$file" "$CLAUDE_DIR/$file"
        echo "  ✓ Linked $file"
    fi
done

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code to load new configuration"
echo "  2. Run '/agents' to see available agents"
echo "  3. Run '/skills' to see available skills"
```

#### sync.sh

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

command=${1:-status}

case "$command" in
    status)
        echo "📊 Sync Status"
        echo ""
        echo "Repository: $SCRIPT_DIR"
        echo "Target: $CLAUDE_DIR"
        echo ""
        git -C "$SCRIPT_DIR" status --short
        ;;
    
    push)
        echo "⬆️ Pushing changes..."
        git -C "$SCRIPT_DIR" add .
        git -C "$SCRIPT_DIR" commit -m "Update Claude configuration" || true
        git -C "$SCRIPT_DIR" push
        echo "✅ Pushed!"
        ;;
    
    pull)
        echo "⬇️ Pulling changes..."
        git -C "$SCRIPT_DIR" pull
        echo "✅ Pulled!"
        ;;
    
    add)
        type=$2
        name=$3
        source_path="$CLAUDE_DIR/$type/$name"
        dest_path="$SCRIPT_DIR/$type/$name"
        
        if [ -z "$type" ] || [ -z "$name" ]; then
            echo "Usage: sync.sh add <type> <name>"
            echo "  type: agents, skills, commands, rules"
            echo "  name: name of the item to add"
            exit 1
        fi
        
        if [ -e "$source_path" ]; then
            mkdir -p "$(dirname "$dest_path")"
            cp -r "$source_path" "$dest_path"
            echo "✓ Added $type/$name to repository"
        else
            echo "❌ $source_path not found"
            exit 1
        fi
        ;;
    
    backups)
        echo "📦 Available backups:"
        ls -la "$HOME" | grep claude-backup || echo "  No backups found"
        ;;
    
    undo)
        latest_backup=$(ls -d "$HOME"/.claude-backup-* 2>/dev/null | tail -1)
        if [ -n "$latest_backup" ]; then
            echo "🔄 Restoring from $latest_backup"
            rm -rf "$CLAUDE_DIR"
            mv "$latest_backup" "$CLAUDE_DIR"
            echo "✅ Restored!"
        else
            echo "❌ No backup found"
            exit 1
        fi
        ;;
    
    *)
        echo "Usage: sync.sh [status|push|pull|add|backups|undo]"
        exit 1
        ;;
esac
```

### Option 2: Plugin Marketplace Setup

#### Create Personal Marketplace

```bash
# Initialize marketplace repository
mkdir -p ~/repos/claude-plugins/.claude-plugin
cd ~/repos/claude-plugins

# Create marketplace.json
cat > .claude-plugin/marketplace.json << 'EOF'
{
  "name": "my-plugins",
  "display_name": "My Plugin Marketplace",
  "description": "Personal collection of Claude Code plugins",
  "plugins": [
    {
      "name": "datascience-team",
      "path": "datascience-team",
      "version": "1.0.0"
    },
    {
      "name": "gamedev-team",
      "path": "gamedev-team",
      "version": "1.0.0"
    }
  ]
}
EOF

# Initialize git
git init
git add .
git commit -m "Initial marketplace setup"

# Push to GitHub (create repo first)
git remote add origin https://github.com/yourusername/claude-plugins.git
git push -u origin main
```

#### Register and Install Plugins

```bash
# In Claude Code, register marketplace
/plugin marketplace add yourusername/claude-plugins

# List available plugins
/plugin list

# Install for current project
/plugin install datascience-team@my-plugins --project .

# Install globally
/plugin install datascience-team@my-plugins
```

---

## Bootstrap Scripts

### New ML Project Bootstrap

#### init-ml-project.sh

```bash
#!/bin/bash
set -e

PROJECT_NAME=${1:?"Usage: init-ml-project.sh <project-name>"}
PROJECT_DIR="$HOME/projects/$PROJECT_NAME"

echo "🚀 Initializing ML project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Initialize git
git init

# Create Python project structure
mkdir -p src tests notebooks data/{raw,processed,external} models reports

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "PROJECT_NAME_PLACEHOLDER"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "scikit-learn>=1.3",
    "matplotlib>=3.7",
    "seaborn>=0.12",
    "jupyter>=1.0",
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[project.optional-dependencies]
dev = [
    "black",
    "ruff",
    "mypy",
    "pre-commit",
]
deep-learning = [
    "torch>=2.0",
    "transformers>=4.30",
]
EOF

sed -i '' "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" pyproject.toml 2>/dev/null || \
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" pyproject.toml

# Create CLAUDE.md
cat > CLAUDE.md << 'EOF'
# Project: PROJECT_NAME_PLACEHOLDER

## Overview
Machine learning project for [describe purpose].

## Tech Stack
- Language: Python 3.11+
- ML Framework: scikit-learn, PyTorch (optional)
- Data: pandas, numpy
- Visualization: matplotlib, seaborn

## Directory Structure
- `src/` - Source code (data processing, models, evaluation)
- `tests/` - Unit and integration tests
- `notebooks/` - Jupyter notebooks for exploration
- `data/` - Data files (raw, processed, external)
- `models/` - Saved model artifacts
- `reports/` - Generated reports and figures

## Common Commands
```bash
# Environment
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Development
pytest                    # Run tests
pytest --cov=src         # Run with coverage
ruff check src tests     # Lint
black src tests          # Format

# Jupyter
jupyter lab
```

## Code Conventions
- Use type hints for all functions
- Write docstrings for public functions
- Keep notebooks clean (restart & run all before commit)
- Data validation with pandera

## Data Pipeline
1. Raw data → `data/raw/`
2. Processing scripts → `src/data/`
3. Processed data → `data/processed/`
4. Models → `models/`
5. Reports → `reports/`
EOF

sed -i '' "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" CLAUDE.md 2>/dev/null || \
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" CLAUDE.md

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Data
data/raw/*
data/processed/*
!data/**/.gitkeep

# Models
models/*
!models/.gitkeep

# Jupyter
.ipynb_checkpoints/
*.ipynb_meta

# IDE
.idea/
.vscode/
*.swp

# Claude
.claude/settings.local.json
.claude/handoff-*.md
EOF

# Create .gitkeep files
touch data/raw/.gitkeep data/processed/.gitkeep data/external/.gitkeep models/.gitkeep

# Create src structure
touch src/__init__.py
mkdir -p src/{data,features,models,evaluation}
touch src/data/__init__.py src/features/__init__.py src/models/__init__.py src/evaluation/__init__.py

# Initialize Claude Code plugin
cd "$PROJECT_DIR"
cat > .claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Edit(src/**)",
      "Edit(tests/**)",
      "Edit(notebooks/**)",
      "Write(src/**)",
      "Write(tests/**)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(jupyter:*)",
      "Bash(ruff:*)",
      "Bash(black:*)"
    ]
  }
}
EOF

echo "✅ ML project initialized at $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "  1. cd $PROJECT_DIR"
echo "  2. uv venv && source .venv/bin/activate"
echo "  3. uv pip install -e '.[dev]'"
echo "  4. claude"
echo "  5. /plugin install datascience-team@my-plugins --project ."
```

### New Game Project Bootstrap (Unity)

#### init-unity-project.sh

```bash
#!/bin/bash
set -e

PROJECT_NAME=${1:?"Usage: init-unity-project.sh <project-name>"}
PROJECT_DIR="$HOME/projects/$PROJECT_NAME"

echo "🎮 Initializing Unity project: $PROJECT_NAME"

# Note: Unity project should be created via Unity Hub first
# This script sets up Claude Code integration

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    echo "Please create the Unity project first via Unity Hub"
    exit 1
fi

cd "$PROJECT_DIR"

# Create CLAUDE.md
cat > CLAUDE.md << 'EOF'
# Project: PROJECT_NAME_PLACEHOLDER

## Overview
Unity game project for [describe game].

## Tech Stack
- Engine: Unity [version]
- Language: C# (.NET Standard 2.1)
- Target Platforms: [PC/Mobile/Console]

## Directory Structure
- `Assets/Scripts/` - C# scripts
- `Assets/Prefabs/` - Reusable game objects
- `Assets/Scenes/` - Game scenes
- `Assets/ScriptableObjects/` - Data containers
- `Assets/Art/` - Art assets
- `Assets/Audio/` - Sound and music

## Architecture
- **Managers**: Singleton services (GameManager, AudioManager)
- **Systems**: Reusable gameplay systems
- **Data**: ScriptableObjects for configuration
- **UI**: MVVM pattern for UI

## Conventions
- PascalCase for public members
- camelCase for private members
- Prefix private fields with underscore: `_health`
- Use [SerializeField] for inspector-exposed private fields
- One class per file
- Namespace: `ProjectName.Category`

## Common Tasks
```
# Build
Unity menu: File > Build Settings > Build

# Tests
Unity menu: Window > General > Test Runner

# Code formatting
dotnet format
```

## Current Focus
[What's being worked on]
EOF

sed -i '' "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" CLAUDE.md 2>/dev/null || \
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/" CLAUDE.md

# Create .gitignore for Unity
cat > .gitignore << 'EOF'
# Unity
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Mm]emoryCaptures/
[Uu]ser[Ss]ettings/

# Asset meta
*.pidb.meta
*.pdb.meta
*.mdb.meta

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vs/
*.csproj
*.sln
*.suo
*.user
*.userprefs

# Claude
.claude/settings.local.json
.claude/handoff-*.md
EOF

# Create Claude settings
mkdir -p .claude
cat > .claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Edit(Assets/Scripts/**)",
      "Write(Assets/Scripts/**)",
      "Edit(Assets/ScriptableObjects/**)",
      "Read(**)"
    ]
  }
}
EOF

echo "✅ Unity project Claude integration complete"
echo ""
echo "Next steps:"
echo "  1. cd $PROJECT_DIR"
echo "  2. claude"
echo "  3. /plugin install gamedev-team@my-plugins --project ."
```

---

## Best Practices

### 1. Keep It DRY
- Universal agents at user level (`~/.claude/agents/`)
- Domain specialists in plugins
- Project-specific only when truly unique

### 2. Progressive Disclosure
- Skills should be concise (<500 lines)
- Put detailed docs in separate files
- Use clear descriptions for auto-triggering

### 3. Version Control Everything
- Dotfiles repo for global config
- Plugin repos for domain teams
- Commit project `.claude/settings.json` (but not `.local.json`)

### 4. Security
- Never commit secrets
- Use environment variables
- Gitignore `settings.local.json`
- Review permissions carefully

### 5. Documentation
- Write clear agent descriptions
- Include examples in skills
- Document available commands in CLAUDE.md

### 6. Testing Workflow
- Test agents in isolated sessions first
- Iterate based on actual usage
- Share successful patterns with team

### 7. Context Management
- Keep CLAUDE.md focused and current
- Use handoff documents for session continuity
- Archive old handoffs periodically

---

## Troubleshooting

### Agent Not Being Invoked
1. Check description includes relevant keywords
2. Verify file location and naming
3. Restart Claude Code session
4. Try explicit invocation: "Use the X agent to..."

### Skill Not Loading
1. Verify `SKILL.md` filename (case-sensitive)
2. Check YAML frontmatter syntax
3. Ensure description matches trigger patterns
4. Review skill with `/skills`

### Plugin Installation Fails
1. Verify marketplace URL is correct
2. Check plugin.json syntax
3. Ensure all referenced files exist
4. Try `/plugin marketplace update`

### Hooks Not Running
1. Check matcher pattern syntax
2. Verify command is executable
3. Check timeout settings
4. Review hook output with `--debug` flag

### Sync Issues
1. Check symlinks are valid: `ls -la ~/.claude/`
2. Verify git status in dotfiles repo
3. Run install script again
4. Check for permission issues

---

## Quick Reference

### Directory Locations
| Type | User Level | Project Level |
|------|------------|---------------|
| Agents | `~/.claude/agents/` | `.claude/agents/` |
| Skills | `~/.claude/skills/` | `.claude/skills/` |
| Commands | `~/.claude/commands/` | `.claude/commands/` |
| Rules | `~/.claude/rules/` | `.claude/rules/` |
| Settings | `~/.claude/settings.json` | `.claude/settings.json` |
| Context | `~/.claude/CLAUDE.md` | `./CLAUDE.md` |

### Key Commands
```bash
# Agents
/agents              # List and manage agents

# Skills
/skills              # List available skills

# Plugins
/plugin marketplace add <repo>      # Add marketplace
/plugin install <name>              # Install plugin
/plugin install <name> --project .  # Install for project only
/plugin list                        # List installed
/plugin update <name>               # Update plugin

# Utilities
/compact             # Compact conversation
/clear               # Clear conversation
/status              # Show session status
```

### File Naming
- Agents: `<name>.md`
- Skills: `<folder>/SKILL.md`
- Commands: `<name>.md`
- Rules: `<name>.md`

---

*Last updated: January 2026*