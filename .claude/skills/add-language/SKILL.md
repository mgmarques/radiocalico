<!-- Radio Calico Skill v2.0.0 -->
Scaffold a new i18n language for Radio Calico.

The user will specify a language name and code (e.g., "French" / "fr"). Follow this process:

1. **Translations** (`static/js/player.js`): Add a new language key to every entry in the `_TRANSLATIONS` object. Copy values from `en` and translate them to the target language. Preserve all existing keys — do not remove or rename any.

2. **LLM mapping** (`static/js/player.js`): Add an entry to `_LANG_TO_LLM` mapping the language code to the full language name used in LLM prompts (e.g., `fr: 'French'`).

3. **HTML radio button** (`static/index.html`): Add a radio button in the settings dropdown language section, following the existing pattern for English/Portuguese/Spanish radio buttons: `<input type="radio" name="language" value="{code}"> {Language Name}`.

4. **Tests** (`static/js/player.test.js`): Add test cases for the new language:
   - `t()` returns correct translation for the new language code
   - `applyLanguage()` sets the language and updates DOM elements
   - Translation completeness — new language has all keys that `en` has

5. **Rules** (`.claude/rules/i18n.md`): Update the language count (e.g., "3 languages" → "4 languages") and add the new language to the list.

6. **Docs** (`CLAUDE.md` and `README.md`): Update language lists to include the new language.

IMPORTANT: NEVER translate song metadata (artist names, track titles, album names) — only UI labels.

Remind the user to **Cmd+Shift+R** after changes.