# We Will See — Recorder
The Recorder converts a live browser session into a YAML test case. Instead of
defining steps manually, the user navigates through the target application; the
Recorder intercepts DOM events and transforms them into the step format the
Runner needs for playback.

## How it works
A JavaScript listener is injected into the active page via `driver.execute_script()`.
It registers event handlers and buffers captured events in `window.__app_events__`.
A guard flag (`window.__app_listener_attached__`) prevents double-registration.

Captured event types:

| DOM event | Step type | Details |
|---|---|---|
| `click` | `click` | Filtered to links, buttons, ARIA roles (`button`, `tab`, `menuitem`), submit/checkbox/radio inputs. Metadata: selector, `innerText`, `href`, tag name. |
| `change` | `input` | On `input`, `select`, `textarea`. Metadata: selector, value, `type`. Submit/button/reset/image inputs are filtered out. |
| `mouseup` | `assert_text` | Text selections of 3+ characters are buffered as assertion candidates (max. 200 characters). |
| `keydown` (Enter/Tab) | `key` | Text inputs only; merged with the preceding `input` event as `submit_key` in `_events_to_steps`. |
| `history.pushState` / `popstate` | `navigate` | Captures client-side route changes (SPA), not just full page loads. |

Each event object carries a Unix millisecond timestamp (`ts`) and the current
`location.href`, which the conversion pipeline uses for step ordering and wait insertion.

### Selector strategy (`bestSelector`)

The listener computes a CSS selector for each interacted element using the following precedence:

1. `#id` — unique and layout-independent
2. Stable attribute: `[data-testid]`, `[data-cy]`, `[name]`, `[aria-label]`
3. Structural path: up to four ancestors, sibling disambiguation via `:nth-of-type(n)`

Positional selectors are only generated as a last resort, as they break when the DOM changes.

### Password masking

`input` events on fields with `type="password"` are buffered with `value = "***"`.
`_events_to_steps` replaces this placeholder with an empty string, so plaintext
passwords are never serialized into the YAML. Credentials are managed in the `meta`
block instead and injected separately at runtime.

## Part 2 — `SessionRecorder` (Python)

`SessionRecorder` wraps the Selenium WebDriver and controls the recording lifecycle.

- **`start()`** — injects the listener via `execute_script`, initialises internal
  state, and starts a daemon thread that calls `_poll_once` every `POLL_INTERVAL` (0.8 s).
- **`stop()`** — sets the stop flag, joins the thread, and drains remaining events
  from `window.__app_events__`.
- **`event_count()`** — returns the length of the current event list (for the GUI status counter).
- **`to_yaml(...)`** — runs the conversion pipeline and serializes the result (see Part 3).

### Poll cycle and re-injection

`_poll_once` performs two operations on each call:

1. **Navigation detection.** If `driver.current_url` differs from the last stored URL,
   a synthetic `navigate` event is created and the listener is re-injected. This is
   necessary because a full page load destroys the JavaScript context — without
   re-injection, capture silently stops after the first navigation.
2. **Event drain.** An `execute_script` call reads `window.__app_events__`, resets
   the array to `[]`, and returns the events; these are appended to the Python-side event list.

All WebDriver calls in the poll cycle are guarded with a broad except clause.
Transient errors (page mid-navigation, brief driver unavailability) are discarded
rather than terminating the recording.

## Part 3 — Conversion pipeline

`to_yaml(...)` passes the event list through three stages:

```
_events_to_steps(events) → _deduplicate(steps) → PyYAML serialization
```

### `_events_to_steps`

Linear pass; each event is mapped to a step type:

- **`navigate`** → `link` step with `url` (only on an effective URL change).
- **`input`** → `form_input` step with selector and value. If a `key` event follows
  immediately, it is consumed and appended to the step as `submit_key`.
  Masked passwords (`***`) are normalized to an empty string.
- **`assert_text`** → `assert_text` step with the selected text.
- **`click`** → `link` step for anchors with a non-`javascript:` `href`; otherwise
  a `click` step with selector and label text.

**Wait insertion.** For each pair of events the timestamp delta is calculated.
If it exceeds `_MIN_WAIT_MS` (1500 ms), an explicit `wait` step is inserted.
The duration is `min(delta, _MAX_WAIT_MS)` (cap: 8000 ms), rounded to one decimal place.
This behaviour can be disabled entirely with `no_wait=True`.

**`source_url` tracking.** The converter tracks the most recently seen URL.
When the URL changes between two steps, it sets `source_url` on the step so the
Runner knows the starting context.

### `_deduplicate`

Second pass for noise reduction:

- Identical consecutive steps are reduced to one.
- A `link` step that immediately follows a `link` step to the same URL is discarded.

### Serialization

The steps are embedded in a `{meta, testcases}` document and serialized with
`yaml.dump(..., allow_unicode=True, default_flow_style=False)`.
The `meta` block contains the base URL and — only when explicitly provided — a
non-default browser identifier and the runtime credentials.

## Orchestration — `run_record(...)`

`run_record(...)` connects the `SessionRecorder` to a full browser session:

1. Instantiates a **non-headless** browser via the browser adapter.
2. Runs the login flow if credentials were provided; uses the resulting URL as the starting point.
3. Creates a `SessionRecorder` and calls `start()`.
4. Runs a 1 Hz ticker that pushes `event_count()` to the GUI.
5. Polls `driver.current_url` in the main loop. A `WebDriverException` signals that
   the user closed the browser — the loop then exits cleanly.
6. Calls `recorder.stop()` and then `to_yaml(...)` with the test case name, URL,
   browser identifier, and credentials.
7. Persists the YAML via `save_testcase(...)` and sends a completion event to the GUI.

A `finally` block closes the browser and resets the run state, ensuring that browser
crashes and early user cancellations leave no inconsistent state.

## Design decisions

- **Capture in JS, interpretation in Python.** The injected listener records only raw
  DOM facts. All semantics (wait thresholds, submit-key merging, duplicate detection)
  are implemented in Python, where they are unit-testable and iterable without a browser context.
- **Re-injection on navigation** is the prerequisite for being able to record multi-page
  apps completely — not just SPAs with client-side routing.
- **Stable selectors** and **automatic waits** are the two most important factors for
  reliable replay: a selector that breaks on layout changes and a missing wait on
  asynchronous loading make test cases non-deterministic.
