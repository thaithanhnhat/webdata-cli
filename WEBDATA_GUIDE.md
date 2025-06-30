# WebData CLI - AI Guide

## Quick Start
```bash
webdata start-chrome
webdata get-text --stream
webdata cleanup --auto
```

## Core Commands

### Chrome
- `webdata start-chrome` - New instance (default, optimal)
- `webdata start-chrome --reuse-existing` - Reuse existing (slower)

### Data Extraction
- `webdata get-text --stream` - Text content → terminal
- `webdata capture-page --stream` - Full page → terminal
- `webdata remote <selenium_cmd> --stream` - Any Selenium → terminal

### Remote (Unlimited Selenium)
- `webdata remote get "URL" --stream` - Auto-captures interface + screenshot
- `webdata remote send_keys "selector" "text" --stream`
- `webdata remote click "selector" --stream`
- `webdata remote execute_script "JS_CODE" --stream`
- `webdata remote scroll_info --stream`
- `webdata remote smart_scroll 1000 --stream`

## Auto-Capture (NEW!)
```bash
# When you navigate, interface state + screenshot auto-captured
webdata remote get "https://site.com" --stream
# Returns: navigation result + interface_state + screenshot path
# Screenshot saved to: data\current-interface.jpg (fixed path)
```

**AI Priority**: Read interface_state from terminal first. Only check screenshot if terminal data unclear.

## Automation Strategy

### Known Sites (Predict)
```bash
# Google, GitHub, common patterns - safe to predict
webdata remote send_keys "textarea[name='q']" "query" --stream
webdata remote execute_script "document.querySelector('form').submit()" --stream
```

### Unknown Sites (Auto-Captured)
```bash
# New/custom sites - auto-capture shows interface
webdata remote get "https://unknown-site.com" --stream
# AI gets: interface_state (forms, buttons, links) + screenshot
# Then act based on captured info
```

## Workflows

### Simple Extraction
```bash
webdata start-chrome
webdata get-text --stream
webdata cleanup --auto
```

### Smart Automation (Auto-Capture)
```bash
webdata start-chrome
webdata remote get "URL" --stream  # Auto-captures interface + screenshot
# AI gets interface_state automatically, no need for separate observe step
webdata remote send_keys "[from_interface_state]" "text" --stream
webdata cleanup --auto
```

## Rules

### When to Observe
- Unknown websites
- After page loads/redirects
- Before complex actions
- Dynamic/SPA sites

### When to Predict
- Google: `textarea[name='q']`
- GitHub: `.Header-link[href='/login']`
- Common e-commerce patterns
- Well-known form structures

### Streaming Usage
- Use `--stream` for real-time observation
- Stream to see actual interface state
- Stream for verification after actions
- Traditional `--output` only for persistent storage

## Best Practices
1. Start: `webdata start-chrome`
2. Navigate: `remote get "URL" --stream` (auto-captures interface)
3. **Read terminal data first**: Use interface_state from stream
4. **Check image only if needed**: `data\current-interface.jpg` if terminal unclear
5. Act: Based on interface_state
6. Cleanup: `webdata cleanup --auto`

## When to Check Screenshot
**Only check `data\current-interface.jpg` if:**
- Terminal interface_state is unclear/incomplete
- Need to see visual layout/positioning
- Debugging complex interactions
- Verifying visual elements

**Don't check image for:**
- Standard forms/buttons (use interface_state)
- Text content (use pageText)
- Link navigation (use links array)
- Error detection (use errors array)

## Critical
- **ALWAYS cleanup**: `webdata cleanup --auto`
- **Terminal first, image second**: Prioritize interface_state
- **Fixed screenshot path**: `data\current-interface.jpg`
- **Verify actions**: Use streaming to check results

## Uninstall
```bash
webdata uninstall  # Complete removal (package + data)
```

## Common Patterns
```bash
# Inspect page
webdata remote execute_script "return {
  url: location.href,
  title: document.title,
  forms: document.forms.length,
  inputs: document.querySelectorAll('input').length,
  buttons: document.querySelectorAll('button').length
}" --stream

# Form automation
webdata remote send_keys "#field" "value" --stream
webdata remote click "#submit" --stream

# Navigation
webdata remote click "a[href='/path']" --stream

# Wait/scroll
webdata remote wait_for_load 5 --stream
webdata remote smart_scroll 1000 --stream
```

---
**Key**: Stream to observe real interface, predict only on known sites, always cleanup.
