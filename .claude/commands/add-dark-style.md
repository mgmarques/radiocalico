<!-- Radio Calico Skill v2.0.0 -->
Add dark mode styling for a new CSS component in Radio Calico.

The user will describe a component or class name. Follow this process:

1. **Read** `static/css/player.css` to understand the current token system and dark mode pattern.

2. **Base tokens** (`:root`): `--mint: #D8F2D5`, `--forest: #1F4E23`, `--teal: #38A29D`, `--orange: #EFA63C`, `--charcoal: #231F20`, `--cream: #F5EADA`, `--white: #FFFFFF`

3. **Dark tokens** (`[data-theme="dark"]`): `--mint: #1a3a1c`, `--forest: #7ecf84`, `--teal: #245e5b`, `--orange: #EFA63C`, `--charcoal: #e0e0e0`, `--cream: #1a1a1a`, `--white: #121212`

4. **Write the base style** using CSS custom properties (`var(--token)`) wherever possible so it automatically adapts to dark mode via token overrides.

5. **Add explicit dark overrides** in the `/* Dark Mode Overrides */` section at the bottom of `player.css` ONLY for properties that can't use tokens (e.g., hardcoded `#fff` backgrounds, specific border colors, box shadows).

6. **Dark mode override patterns** already used in the project:
   - `[data-theme="dark"] .component { background: #1e1e1e; border-color: #333; }`
   - `[data-theme="dark"] .component { color: #ccc; }` or `color: #aaa;`
   - Box shadows: `rgba(0,0,0,0.4)` instead of `rgba(0,0,0,0.12)`

Remind the user to **Cmd+Shift+R** after changes.
