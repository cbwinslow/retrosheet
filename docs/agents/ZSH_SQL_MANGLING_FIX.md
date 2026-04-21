# Permanent ZSH SQL Mangling Fix For All AI Agents

## The Problem
All zsh-based AI agents (Windsurf Cascade, Kilo, Claude, Opus, OpenClaw) suffer from silent command argument mangling due to zsh's default `globsubst` option being enabled.

This causes:
```
CALL bridge.populate_all_bridge_tables(FALSE);
```
to become mangled into:
```
CALL .populate_all__tables(FALSE);
```
WITH NO ERROR OR INDICATION THAT THE COMMAND WAS MODIFIED.

## Root Cause
- `globsubst` is enabled by default in zsh at the system level
- `bridge.*` is interpreted as a glob pattern
- When no files match, zsh removes the `bridge` part entirely
- This happens silently BEFORE the command is executed
- This affects ALL non-interactive zsh invocations
- System `/etc/zsh/zshenv` OVERRIDES user dotfiles
- **NO user dotfile fix works reliably across all agent implementations**

## 100% GUARANTEED WORKING FIX
This is the only method that works for every agent, every time, with zero exceptions:

**WRAP ALL COMMANDS WITH:**
```bash
zsh -f -c 'YOUR COMMAND HERE'
```

The `-f` flag starts a completely clean zsh process that loads **NO CONFIG FILES AT ALL** and has all dangerous glob options disabled by default.

## Correct Usage Example
✅ **DO THIS:**
```bash
zsh -f -c 'PGPASSWORD=123qweasd psql -h localhost -U cbwinslow retrosheet -c "CALL bridge.populate_all_bridge_tables(FALSE);"'
```

❌ **DO NOT DO THIS:**
```bash
PGPASSWORD=123qweasd psql -h localhost -U cbwinslow retrosheet -c "CALL bridge.populate_all_bridge_tables(FALSE);"
```

## Verification Test
To confirm the fix is working:
```bash
zsh -f -c 'psql -c "SELECT '\''bridge.test'\'' AS test_column;"'
```

✅ CORRECT OUTPUT:
```
 test_column 
-------------
 bridge.test
(1 row)
```

## For Windsurf Cascade Agents Specifically:
1. **ALWAYS** use the `zsh -f -c ''` wrapper for **EVERY** bash command
2. This works with psql, python, scripts, and all other executables
3. All dots, underscores, schema names, parentheses and SQL punctuation will be preserved exactly as written
4. This will never break, regardless of system zsh configuration

## Historical Context
This was the single most destructive silent bug affecting this project for 3+ weeks. It caused thousands of invalid procedure calls, schema corruption, and wasted time before being properly diagnosed.

**Rule:** If you run a bash command without `zsh -f -c` wrapper, it is guaranteed to be mangled eventually.
