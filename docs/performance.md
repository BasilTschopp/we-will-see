# We Will See — Performance Measurement

This is not a classic performance test. The values serve as an indicator: if a new release shows a significantly higher load time across multiple steps compared to previous runs, that is a signal worth investigating, not a precise measurement of the cause.

## What is measured
Every test step records a `load_time_ms` value. The timer starts at the beginning of
the step handler and stops as soon as the target element has been found or the
navigation has completed, before the post-action DOM stability wait.

For navigation steps (`link`) this covers the time from `driver.get()` until the
`<body>` tag is present. For interaction steps (`click`, `nav_click`, `form_input`,
etc.) it covers element lookup plus any page load triggered to reach the source URL.

The value is stored in milliseconds and displayed alongside each result.

## What it is not
The measured time is a wall-clock duration as seen by Selenium and includes:

- Selenium overhead and WebDriver communication latency
- Element search time (CSS selector matching across the DOM)
- Any waits introduced by the test runner itself

It does not isolate server response time, network throughput, or rendering time.
No load is generated. Every run is a single sequential or per-test-case browser
session. The numbers are useful for spotting pages that are noticeably slow or that
regress between runs, but they should not be interpreted as benchmark results.