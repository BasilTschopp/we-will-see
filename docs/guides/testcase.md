# We Will See — YAML Test Case Format

A test case is stored as a single YAML document. It is the central interface of the
tool: the recorder produces this format, the runner consumes it, and it is what a
user edits when adjusting a test by hand. This document describes its structure.

The relevant code is `usecases/testcase_reader.py` (parsing), `models/models.py`
(the target `NavigationItem` structure) and `usecases/testcase_runner.py`
(execution per step type).

## Top-level structure

A document has exactly two top-level keys:

```yaml
meta:
  url: https://example.com
  browser: chrome
  username: alice
  password: secret
testcases:
  - method: link
    url: https://example.com/dashboard
    description: "Open dashboard"
  - method: click
    selector: "#save-button"
    description: "Click save"
```

- **`meta`** — run-level parameters (target URL, browser, credentials, flags).
- **`testcases`** — an ordered list of steps. Each list entry becomes one
  `NavigationItem` and is executed in order.

If the top level is not a mapping, or the YAML is invalid, the reader logs a warning
and returns an empty test case rather than raising — so a malformed file cannot
crash a run.

## The `meta` block

All keys are optional except `url` (without a URL the run aborts). When several test
cases are combined into one run, their `meta` blocks are merged and later values
win.

| Key | Type | Meaning |
|-----|------|---------|
| `url` | string | Target application URL. Required for a run; also the login/start page. |
| `browser` | string | `chrome`, `edge` or `firefox`. Anything else falls back to `chrome`. |
| `username` | string | Optional login username. |
| `password` | string | Optional login password. |
| `private` | bool | Open the browser in private/incognito mode. |

> Credentials in `meta` are stored as written. They are only encrypted when saved as
> a reusable *preset* (see the security documentation), not inside the YAML itself.

## The `testcases` list

Each step is a mapping. The only field that is always meaningful is `method`, which
selects how the step is executed. The remaining fields are read into the
`NavigationItem` with these defaults:

| Field | Default | Used for |
|-------|---------|----------|
| `method` | `link` | Step type (see table below). |
| `url` | `""` | Target URL for `link` steps. |
| `description` | `""` | Human-readable label shown in logs and results. |
| `element_text` | `""` | Visible text used to locate an element. |
| `source_url` | `""` | Page the step should start from before acting. |
| `selector` | `""` | CSS selector used to locate an element. |
| `input_value` | `""` | Value typed into a field, or the wait duration in seconds. |
| `submit_key` | `""` | Key pressed after input (`enter`, `return`, `tab`, `escape`). |
| `assert_text` | `""` | Text expected to be present on the page. |
| `depth` | `0` | Crawl-depth metadata (informational). |

Any field not present in the YAML simply takes its default; unknown extra fields are
ignored.

## Step methods

The `method` value determines which fields matter. The following are recognized by
the runner.

| `method` | Purpose | Primary fields |
|----------|---------|----------------|
| `link` | Navigate to a URL (handles `#` hash navigation and JS/OAuth redirects). | `url` |
| `click` | Click an element by CSS selector. | `selector`, `source_url` |
| `form_input` | Type a value into a field, optionally submit with a key. | `selector`, `input_value`, `submit_key`, `source_url` |
| `assert_text` | Verify text is present on the page or inside an element. | `assert_text` (or `input_value`), optional `selector`, `source_url` |
| `wait` | Pause for a number of seconds. | `input_value` (seconds) |
| `nav_click` | Click a navigation element matched by visible text. | `element_text`, `source_url` |
| `modal` | Open a modal/dialog and confirm it appears. | `element_text`, `source_url` |
| `tab` | Switch an ARIA tab and detect a DOM change. | `element_text`, `source_url` |
| `pagination` | Click a pagination control (matched by aria-label). | `element_text`, `source_url` |
| `table_row` | Click the first data row of a table. | `source_url` |

A step whose `method` is not in this list is skipped (no handler is dispatched).

### Notes on specific fields

- **`source_url`** — for action steps (`click`, `form_input`, `nav_click`, …) this
  tells the runner which page to be on before acting. If the browser is already on
  that page, it is not reloaded; otherwise the runner navigates there first.
- **`input_value`** — overloaded by design: it is the typed text for `form_input`,
  and the number of seconds for `wait`.
- **`assert_text`** — the `assert_text` handler accepts the expected text in either
  `assert_text` or `input_value`; if a `selector` is given, only that element's text
  is searched, otherwise the whole page body.
- **`submit_key`** — mapped case-insensitively to a real key press. Unrecognized
  values are ignored (the value is still typed, just not submitted).

## How the recorder fills the fields

When a test case is recorded rather than written by hand, the recorder maps captured
browser events to steps:

- a navigation or a link click with a real `href` → `link` (with `url`)
- a non-link click → `click` (with `selector`, and `source_url` if the page changed)
- a field change → `form_input` (with `selector` and `input_value`); a following
  Enter/Tab is merged in as `submit_key`
- selecting text on the page → `assert_text` (with the selected text in
  `input_value`)
- a pause longer than ~1.5s between events → an explicit `wait` step

Passwords typed during recording are masked and not written into the YAML. Selectors
are generated to be as stable as possible (preferring `id`, then `data-testid`,
`name`, `aria-label`, then a short structural path).

## Worked example

```yaml
meta:
  url: https://shop.example.com
  browser: chrome
  username: testuser
  password: testpass
testcases:
  # 1. land on the start page after login
  - method: link
    url: https://shop.example.com/
    description: "Open start page"

  # 2. open the products section from the nav bar
  - method: nav_click
    element_text: "Products"
    source_url: https://shop.example.com/
    description: "Go to products"

  # 3. search for an item
  - method: form_input
    selector: "#search"
    input_value: "Notebook"
    submit_key: enter
    source_url: https://shop.example.com/products
    description: "Search for Notebook"

  # 4. give the results a moment to load
  - method: wait
    input_value: "2"
    description: "Wait 2s"

  # 5. open the first result row
  - method: table_row
    source_url: https://shop.example.com/products?q=Notebook
    description: "Open first result"

  # 6. confirm the product page shows the expected text
  - method: assert_text
    assert_text: "Add to cart"
    description: "Product page loaded"
```

Running this produces one result per step, each with status `OK` or `ERROR`,
timing and (on failure) an error detail.

## Validation behaviour

The format is intentionally lenient:

- Missing optional fields take defaults.
- Invalid YAML or a non-mapping top level yields an empty test case (logged as a
  warning), not an exception.
- An unknown `method` is silently skipped at execution time.
- Unknown extra fields are ignored.

This keeps the tool resilient: a single bad step or stale field degrades gracefully
instead of aborting the whole run.
