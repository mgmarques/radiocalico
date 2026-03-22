# 📘 CLAUDE.md Best Practices Guide
A `CLAUDE.md` file is essentially **instructions + context for an AI agent (like Claude)** working in your repo. The quality of this file directly affects how useful and reliable the agent is.

Here’s a clean, scannable summary you can quickly reference:

---

## ✅ Do vs ❌ Don’t

| ✅ Do                                         | ❌ Don’t                            |
| -------------------------------------------- | ---------------------------------- |
| Be explicit about goals and purpose          | Be vague (“summarize nicely”)      |
| Define clear scope (what to include/exclude) | Let the agent assume context       |
| Use step-by-step instructions                | Write long unstructured paragraphs |
| Provide exact commands (CLI, scripts)        | Use ambiguous instructions         |
| Include example outputs                      | Expect the agent to infer format   |
| Define tone and style                        | Leave writing style undefined      |
| Handle edge cases                            | Ignore missing or incomplete data  |
| Keep sections modular and structured         | Mix multiple responsibilities      |
| Keep it updated and version-controlled       | Let it become outdated             |

---

## 🧠 Recommended Structure

| Section              | What to Include                                  |
| -------------------- | ------------------------------------------------ |
| **Purpose**          | What the agent should accomplish                 |
| **Context**          | Commands, data sources (e.g., PR diff, comments) |
| **Scope**            | What to include and exclude                      |
| **Instructions**     | Step-by-step actions                             |
| **Output Format**    | Exact response structure                         |
| **Style Guidelines** | Tone, formatting rules                           |
| **Edge Cases**       | Fallback behavior                                |

---

## ⚡ Golden Rules

* **Clarity > cleverness**
* **Structure > paragraphs**
* **Explicit > implicit**
* **Examples = better results**
* **Treat it like code, not documentation**

---

Here’s more details about it, below a practical, no-fluff guide.

## ✅ DO (Best Practices)

### 1. Be explicit about goals

Tell the agent exactly what it’s supposed to do.

**Good**

```markdown
## Purpose
Summarize pull requests with a focus on:
- Breaking changes
- Performance impact
- Security implications
```

---

### 2. Define scope clearly

Limit what the agent should touch.

```markdown
## Scope
- Only analyze files changed in the PR
- Ignore generated files (dist/, build/)
```

---

### 3. Give step-by-step instructions

Agents perform better with structured steps.

```markdown
## Steps
1. Read PR diff
2. Identify key changes
3. Categorize changes (feature, fix, refactor)
4. Generate summary
```

---

### 4. Include concrete commands

If your workflow depends on CLI tools, specify them.

```markdown
- PR diff: !'gh pr diff'
- Comments: !'gh pr view --comments'
```

---

### 5. Show examples of good output

This is one of the highest-impact improvements.

```markdown
## Example Output
### Summary
- Adds user authentication
- Fixes memory leak in cache

### Risks
- May affect login performance
```

---

### 6. Define tone and style

Avoid vague outputs by constraining writing style.

```markdown
## Style
- Be concise
- Use bullet points
- Avoid speculation
```

---

### 7. Keep it modular

Break into sections:

* Purpose
* Context
* Instructions
* Output format

---

### 8. Keep it version-controlled and updated

Treat it like code:

* Update when workflows change
* Review in PRs

---

## ❌ DON’T

### 1. Don’t be vague

❌ “Summarize the PR nicely”
→ Too ambiguous

---

### 2. Don’t overload with irrelevant info

Avoid dumping your whole README or architecture unless needed.

---

### 3. Don’t assume implicit knowledge

Agents don’t “just know” your conventions.

❌ “Follow our standard process”
✔ Define the process explicitly

---

### 4. Don’t mix multiple responsibilities

Bad:

```markdown
This agent reviews code, writes tests, deploys, and updates docs
```

Split into separate agents/files instead.

---

### 5. Don’t rely on long paragraphs

Agents work better with:

* bullet points
* short instructions
* structured sections

---

### 6. Don’t forget edge cases

Define what to do when things are missing:

```markdown
If no PR description exists:
- Infer intent from commit messages
```

---

### 7. Don’t leave commands ambiguous

❌

```markdown
- Get PR data
```

✔

```markdown
- PR data: !'gh pr view'
```

---

## 🧠 Strong Recommended Structure

Here’s a solid template you can reuse:

````markdown
```markdown
# CLAUDE.md

## Purpose
What this agent does

## Context
- PR diff: !'gh pr diff'
- PR comments: !'gh pr view --comments'

## Scope
What to include / exclude

## Instructions
1. Step 1
2. Step 2
3. Step 3

## Output Format
Exact structure of the response

## Style Guidelines
Tone, formatting rules

## Edge Cases
What to do when things go wrong
```
````

---

## ⚡ Pro Tips (High Impact)

### ✔ Constrain output format heavily

The more structured, the better:

```markdown
## Output Format
### Summary
- ...

### Changes
- ...

### Risks
- ...
```

---

### ✔ Optimize for repeatability

Your goal is:

> Same input → consistent output

---

### ✔ Think like you're programming, not writing docs

This is not documentation — it's **behavior design**.

---

### ✔ Test and iterate

* Run the agent
* See where it fails
* Tighten instructions

---

# Maintenance

Periodically check the CLAUDE.md file against:
 * Maintains consistency between sessions
 * Contains system architecture
 * How to run tests
 * Formatting preferences
 * # Prefacing something with a hashtag will add it to memory