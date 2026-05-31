# We Will See — Test Execution

## Flow
1. Load the test case.
2. Open a browser.
3. Open the application and optionally log in.
4. Execute steps sequentially.
5. Record `OK` or `ERROR` per step, with load time and page title.
6. Save results.
7. Optionally send an email alert on failure.
8. Close the browser.

## Failure detection
A step fails when:
- Element not found or not visible.
- Error page or error keyword in the title (404, 500, 403 …).
- Body text under 30 characters (page treated as empty).
- Expected text missing from page content (`assert_text`).
- Redirect to a foreign host.

A failed step does not abort the run.

## Parallel execution
Multiple test cases each run in their own browser thread with a separate session and a separate run entry.

## Automated execution
Test cases marked as Automated can be run headless without the GUI via:

```
python3 main.py --automated
```

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
| `modal` | Clicks a modal trigger and verifies a `[role=dialog]` becomes visible |
| `tab` | Clicks a `[role=tab]` and checks for a DOM change |
| `pagination` | Clicks a pagination button by aria-label |
| `table_row` | Clicks the first data row of a table and checks for URL or DOM change |
| `form_input` | Types a value into a CSS-selector field; optionally sends a submit key |
| `click` | Clicks an arbitrary CSS-selector element |
| `assert_text` | Asserts that a string appears in the page body or a scoped element |
| `wait` | Pauses execution for a given number of seconds |

### Result storage
Results are persisted to a local **SQLite** database. Each run gets a name of the form `YY.MM.DD - HH:MM - <testcase>`. Every step stores status, load time in ms, page title, error detail, and a timestamp.

### Email alerts
When a run finishes with at least one ERROR, a failure alert is sent via SMTP. The email contains the run name and the list of failed steps. In CLI mode (`--automated`), alerts are sent for every failing test case independently.