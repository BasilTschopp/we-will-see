# We Will See — Test Execution

## Flow
1. Load the test case(s). Selecting several test cases at once merges their steps
   into a single sequential run, unless parallel execution is enabled (see below).
2. Open a browser.
3. Open the application and optionally log in.
4. Read the release/version label from the page, if a release selector is configured.
5. Execute steps sequentially. Each list-of-values `matrix` entry in `meta` runs the
   whole step list once per combination, producing one result set per iteration.
6. Record `OK` or `ERROR` per step, with load time and page title.
7. Save results.
8. Optionally send an email alert on failure.
9. Close the browser.

## Failure detection
A step fails when:
- Element not found or not visible.
- Error page or error keyword in the title. The keyword list is configurable under
  Settings (`error_page_keywords`); the built-in default covers English and German
  terms (404, 500, 403, "not found", "fehler", "wartungsarbeiten", "nicht erreichbar", …).
- Body text under 30 characters (page treated as empty).
- Expected text missing from page content (`assert_text`).
- Redirect to a foreign host.

A failed step does not abort the run by itself. Two things do abort it:
- A step whose `method` is missing or unrecognized aborts the entire run immediately
  (the step is still recorded as `ERROR` first).
- If **Stop on error** is enabled in Settings, the run aborts after the first `ERROR`
  result of any kind.

## Timeouts and error handling settings
Configurable under Settings:
- **Step timeout** (seconds, 0 = disabled) — a single step is aborted and recorded as
  `ERROR` if it runs longer than this.
- **Run timeout** (minutes, 0 = disabled) — the whole run is stopped if it takes longer
  than this.
- **Stop on error** — abort the run after the first failing step (see above).
- **Screenshot on error** — save a screenshot to `data/screenshots/` for every `ERROR` step.

## Parallel execution
Off by default (Settings toggle). When disabled, all selected test cases run
sequentially in one shared browser session and are merged into a single run.
When enabled, each selected test case runs in its own thread with its own browser
session and its own run entry, all concurrently.

## Test matrix
A `matrix` block under `meta` can pair each step list with parameter combinations:
scalar values are constants, list values are expanded with the Cartesian product of
all list keys. Each combination becomes one run, suffixed with a label built from the
varying values (e.g. `... [chrome, de]`), and its values are available to steps as
`{{key}}` placeholders (see `value_resolver.py`).

## Dynamic values
Step text fields (`description`, `assert_text`, `input_value`, …) may contain
`{{...}}` placeholders resolved at run time:
- `{{random(min,max)}}` — a random integer in the given range.
- `{{today}}`, `{{today+N}}`, `{{today-N}}`, optionally `{{today+N|<strftime format>}}`
  — defaults to `%d.%m.%Y`.
- `{{name}}` — a value previously captured with `store_as` (via `read_value` or
  `form_input`) or a matrix variable.

## Automated execution
Test cases marked as Automated can be run headless without the GUI via:

```
python main.py --automated
```

Each automated test case runs sequentially in its own browser session; a progress
window shows live step status since there is no visible browser overlay.

## Technical details

### Technology
- **Selenium WebDriver** drives the browser; Python `threading.Thread` for parallel runs.
- **Supported browsers**: Chrome (default), Edge, Firefox — each optionally in private/incognito mode.
- Browser window is always opened at 1920 × 1080. Automation flags and the password manager are suppressed.
- Page load timeout: 30 s. Implicit wait: 1 s.

### Driver resolution
The correct WebDriver binary (chromedriver, msedgedriver, geckodriver) is located automatically by matching the major version of the installed browser. On Windows, msedgedriver can be downloaded automatically if no local copy is found.

### Login
When credentials are configured, the runner navigates to the URL and detects username/password fields via a list of common CSS selectors (fallback: first visible `input[type=text/email]`). After submitting, it polls up to 15 s for a redirect away from the login/auth page.

### Cookie banner dismissal
After login, common cookie-consent selectors and button texts are tried automatically. No step definition is required.

### Element wait
Before interacting with a target element (`click`, `form_input`, `assert_text`), the runner uses `WebDriverWait` to wait up to 10 s for the element to be present and clickable. For `link` steps, it waits for the `<body>` tag to appear (up to 10 s) after navigation. This ensures steps don't fail simply because the page hasn't finished rendering yet.

### DOM stability
After every click or navigation, the runner additionally waits until the DOM fingerprint (tag counts + class list hash via JS) has been stable for 250 ms, with a maximum timeout of 8 s. This prevents flaky results on single-page applications.

### Step types
| Method | What is tested |
|---|---|
| `link` | Direct URL navigation; checks for error title, empty body, cross-host redirect |
| `nav_click` | Finds a nav/sidebar element by text and clicks it |
| `table_row` | Clicks the first data row of a table and checks for URL or DOM change |
| `form_input` | Types a value into a CSS-selector field; optionally sends a submit key; can capture the typed value via `store_as` |
| `click` | Clicks an arbitrary CSS-selector element; can be marked `optional` to skip (as `OK`) instead of failing when the element is missing |
| `assert_text` | Asserts that a string appears in the page body or a scoped element |
| `assert_present` | Asserts that an element matching a selector exists and has non-empty text |
| `assert_absent` | Asserts that an element matching a selector does *not* exist, or is empty |
| `log_text` | Reads an element's text and records it in the result, without asserting anything |
| `read_value` | Reads an element's text/value and, with `store_as`, saves it for later `{{...}}` use |
| `wait` | Pauses execution for a given number of seconds |
| `foreach` | Iterates a stored list value (`var`), running its nested `steps` once per item |

`modal`, `tab` and `pagination` steps from earlier versions are no longer supported;
use `click`/`assert_present` with an explicit selector instead.

### Result storage
Results are persisted to a local database, SQLite by default or an external
PostgreSQL instance (configured via Settings > Database, see `dbconfig.py`). Each run
gets a name of the form `YY.MM.DD - HH:MM - <testcase>`, with a matrix label suffix
when applicable. Every step stores status, load time in ms, page title, error detail,
and a timestamp.

### Reports
`report_generator.py` builds a self-contained HTML report per run (or per selection of
runs), either the full step list or errors-only, saved to `data/reports/`.

### Email alerts
When a run finishes with at least one ERROR, a failure alert is sent via SMTP. The email contains the run name and the list of failed steps. In CLI mode (`--automated`), alerts are sent for every failing test case independently.