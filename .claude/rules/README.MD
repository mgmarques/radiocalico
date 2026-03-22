# Scoped rules

Break instructions into focused topic files instead of one monolithic CLAUDE.md.

In a **`.claude/rules/`** setup (used by tools like Claude Code or similar AI-assisted dev environments), **scoped rules** are a way to apply specific instructions only to certain parts of your project instead of globally.

### 🧠 What “scoped rules” means

Scoped rules are rule files that only apply when the AI is working within a particular:

* folder
* file pattern
* feature area
* or context

Instead of one big global rule file, you break rules into smaller, targeted ones.

---

## 📁 Typical structure

```
.claude/
  rules/
    backend.md
    frontend.md
    tests.md
    security.md
```

Each file defines rules for a **specific scope**.

---
# 🧠 How Claude Code rules actually work (important context)

* Rules are injected into the model’s **context window**
* They compete with your **code, prompts, and history**
* The model does **not “remember” rules globally**—they must fit and stay relevant per request
* More rules ≠ better results (often worse)

---

## 🎯 How scoping works

The system determines which rules to apply based on:

* File paths (e.g., `/backend/**`)
* File types (`*.test.ts`, `*.py`)
* Sometimes metadata or naming conventions

---

## ✍️ Example: Backend rules

```
# backend.md

Applies to: /backend/**

- Use TypeScript
- Prefer PostgreSQL
- Follow repository pattern
- Validate all inputs
```

---

## 🎨 Example: Frontend rules

```
# frontend.md

Applies to: /frontend/**

- Use React with hooks
- Prefer functional components
- Use Tailwind for styling
- Avoid inline styles
```

---

## 🧪 Example: Test rules

```
# tests.md

Applies to: **/*.test.ts

- Use Jest
- Mock external services
- Keep tests deterministic
- Aim for high coverage
```

---

## ⚙️ Why use scoped rules

Scoped rules help you:

* Avoid irrelevant instructions cluttering the AI context
* Get more accurate, context-aware code suggestions
* Maintain consistency across different parts of a codebase
* Scale rules as your project grows

---

## 🚨 Best practices

* Keep rules **small and focused**
* Avoid duplication across files
* Use clear “Applies to” patterns
* Put truly global rules in a separate file (e.g., `global.md`)
* Prioritize rules if conflicts might occur

---

## 🧩 Global vs Scoped

| Type   | Applies to     | Use case                          |
| ------ | -------------- | --------------------------------- |
| Global | Entire project | Formatting, naming conventions    |
| Scoped | Specific areas | Frameworks, architecture, testing |

---
# Quick Do's & Don'ts
## Do
- Run /init first
- Use bullet points & short headings
- Put most important guardrails at the top
- Version-control the root CLAUDE.md
- Periodically review & prune (treat like living code)
## Don't
- Dump entire style guides / API docs into it
- @-include huge files unless absolutely necessary
- Write vague / aspirational rules
- Make it > 500 lines without splitting
- Forget to add rules when claude keeps making the same mistake

---

# 🚫 The “Don’t” list: What to avoid when writing rules
Those “Don’t” points map very directly to how **rules actually behave inside Claude Code**—they’re not just guidelines, they’re responses to real limitations of how the system loads and uses rules.

Let’s break the relationship so it’s clear *why each one matters* 👇

---
## 🔗 Mapping each “Don’t” to real behavior

### ❌ “Don’t dump entire style guides / API docs”

**Why:**
Claude doesn’t “study” long docs—it *samples patterns*. Large dumps:

* Waste context tokens
* Dilute important instructions
* Reduce adherence to the parts you actually care about

**Better approach:**

* Extract **enforceable rules**, not reference material

✅ Good:

```
- Use camelCase for variables
- Do not use default exports
```

❌ Bad:

```
Paste entire Airbnb style guide...
```

---

### ❌ “Don’t @-include huge files”

(`@file` or similar includes)

**Why:**

* Included files are treated like raw context
* Large files = **context eviction of more relevant info**
* The model won’t prioritize them intelligently

**Rule of thumb:**

> If it’s > ~100–200 lines, it probably shouldn’t be included

---

### ❌ “Don’t write vague / aspirational rules”

**Why:**
Claude follows **concrete, testable constraints**, not philosophy.

❌ Vague:

```
- Write clean code
- Follow best practices
```

These fail because:

* No clear action
* No measurable outcome

✅ Strong:

```
- Use early returns instead of nested conditionals
- Do not use `any` in TypeScript
```

---

### ❌ “Don’t make it > 500 lines without splitting”

**Why:**

* Large rule files reduce **signal-to-noise ratio**
* Important rules get ignored or truncated
* Context window pressure increases

**This is where scoped rules come in:**

* Split by domain (frontend, backend, tests, etc.)
* Only load what’s relevant

👉 This is the *core connection* to scoped rules:

> Scoped rules exist mainly to avoid this exact problem.

---

### ❌ “Don’t forget to add rules when Claude repeats mistakes”

**Why:**
Claude Code is **stateless learning-wise**:

* It doesn’t improve across sessions
* Repeated mistakes = missing constraints

So rules act as:

> A manual “fine-tuning layer”

**Workflow pattern:**

1. Claude makes mistake
2. You correct it
3. You add a rule
4. Mistake stops recurring

---

## ⚙️ The deeper principle tying all of these together

All the “Don’ts” are enforcing one idea:

> 👉 Rules should be **high-signal, low-noise, enforceable constraints**

---

## 🧩 How this connects to scoped rules

Scoped rules are the **solution** to most of these problems:

| Problem           | Scoped rules fix       |
| ----------------- | ---------------------- |
| Too long          | Split by domain        |
| Irrelevant rules  | Load only what applies |
| Context overflow  | Reduce total tokens    |
| Conflicting rules | Isolate concerns       |

---

## ✅ A strong mental model

Think of rules like:

* ❌ Not documentation

* ❌ Not guidelines

* ❌ Not onboarding material

* ✅ **Compiler hints for an AI**

* ✅ **Constraints, not explanations**

* ✅ **Short, explicit, enforceable**

---

## 🔥 A practical “gold standard”

A good rule file should:

* Be **< 200 lines**
* Contain **only actionable rules**
* Avoid duplication
* Be scoped to a **clear area**
* Read like a **checklist**, not an essay

---
# ✅ The “Do” list: How to write effective rules for Claude Code
These “Do” points are based on how **Claude actually processes and prioritizes instructions**. They’re not just best practices—they’re responses to real behavior of the system.

So, the “Do” list is basically the **operational playbook** for making Claude Code rules *actually stick in practice*. Each item is tied to how the system prioritizes, loads, and “pays attention” to instructions.

Here’s how they connect to real behavior 👇

---

## 🧠 1. “Run /init first”

**What it does:**

* Bootstraps a `CLAUDE.md`
* Establishes a baseline structure for rules
* Often includes default conventions (formatting, workflows, etc.)

**Why it matters:**
Without `/init`, you’re starting from a blank slate, which means:

* No consistent entry point for rules
* Higher chance of fragmented or duplicated instructions

👉 Think of it as:

> Creating the “root contract” between you and Claude

---

## 🧩 2. “Use bullet points & short headings”

**Why this is critical:**

Claude parses rules more reliably when they are:

* Scannable
* Structured
* Chunked into atomic instructions

Compare:

❌ Hard to follow:

```text
When writing backend code you should generally try to validate inputs and avoid nesting and prefer readability over cleverness...
```

✅ Easy to follow:

```text
## Backend Rules
- Validate all inputs
- Use early returns (avoid deep nesting)
- Prefer readability over cleverness
```

**Why it works:**

* The model “locks onto” list patterns
* Each bullet becomes a discrete constraint

---

## 🚨 3. “Put most important guardrails at the top”

**This one is huge.**

Claude gives **more weight to earlier content** in the context.

So:

* Top rules → high adherence
* Bottom rules → often ignored if context is tight

👉 This is essentially **priority encoding by position**

**Example:**

```text
# Critical Rules
- Never use `any` in TypeScript
- Do not access production database directly

# Secondary Rules
- Prefer small functions
```

---

## 📦 4. “Version-control the root CLAUDE.md”

**Why:**
Your rules are **part of your codebase behavior**, not just notes.

Benefits:

* Track what changed when behavior changes
* Collaborate with team on AI constraints
* Revert bad rule changes
* Keep environments consistent

👉 Treat it like:

> `tsconfig.json` or `eslint.config.js` for your AI

---

## 🔄 5. “Periodically review & prune (living code)”

**Why this matters:**

Rules naturally degrade over time:

* Some become irrelevant
* Some conflict
* Some are never triggered
* Some are redundant

And too many rules = worse performance

👉 Remember:

> Every extra rule competes for attention

---

### 🧪 What “pruning” actually looks like

Remove rules that are:

* ❌ Never violated
* ❌ Duplicated elsewhere
* ❌ Too vague to enforce
* ❌ Obsolete (tech stack changed)

Refactor rules that:

* Are too long → split
* Are too broad → scope them
* Conflict → consolidate

---

## 🔗 How this “Do” list connects to the “Don’t” list

They’re mirror images:

| Don’t                    | Do                     |
| ------------------------ | ---------------------- |
| Dump huge docs           | Keep rules concise     |
| Include large files      | Structure clearly      |
| Be vague                 | Use bullet constraints |
| Let rules grow huge      | Split + prune          |
| Ignore repeated mistakes | Maintain actively      |

---

## 🧠 The deeper principle

Together, both lists enforce this:

> 👉 Claude performs best with **small, structured, prioritized, actively maintained constraints**

---

## ⚙️ A strong real-world setup

**Root `CLAUDE.md`:**

```id="9ev0q1"
# Critical Guardrails
- Do not use `any` in TypeScript
- Always validate external inputs

# General Conventions
- Use descriptive variable names
- Prefer early returns
```

**Scoped rules:**

```
.claude/rules/
  frontend.md
  backend.md
  tests.md
```

---

## 🔥 Mental model to keep

Think of your rules as:

* A **ranking system** (top = strongest)
* A **budget** (every line costs attention)
* A **feedback loop** (update when mistakes happen)

---
