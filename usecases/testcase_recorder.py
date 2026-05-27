"""
recorder.py â€“ Session recorder for Bugula.

Injects a JavaScript listener into the live browser page that captures:
  - clicks  (with a stable CSS selector)
  - input / change events (text, select, checkbox)
  - navigations (URL changes)

Collected events are polled via driver.execute_script and converted to
NavigationItem / YAML testcase format.
"""

import time
import yaml
from typing import Optional
from models.models import log


_RECORDER_JS = r"""
(function () {
    if (window.__bugula_recorder_active__) return;
    window.__bugula_recorder_active__ = true;
    window.__bugula_events__ = window.__bugula_events__ || [];

    function bestSelector(el) {
        if (!el || el === document.body) return 'body';
        if (el.id) return '#' + CSS.escape(el.id);
        for (const attr of ['data-testid','data-cy','name','aria-label']) {
            const v = el.getAttribute(attr);
            if (v) return el.tagName.toLowerCase() + '[' + attr + '="' + v.replace(/"/g,'\\"') + '"]';
        }
        const parts = [];
        let cur = el;
        for (let i = 0; i < 4 && cur && cur !== document.body; i++) {
            let tag = cur.tagName.toLowerCase();
            const siblings = cur.parentElement
                ? Array.from(cur.parentElement.children).filter(c => c.tagName === cur.tagName)
                : [];
            if (siblings.length > 1) {
                const idx = siblings.indexOf(cur) + 1;
                tag += ':nth-of-type(' + idx + ')';
            }
            parts.unshift(tag);
            cur = cur.parentElement;
        }
        return parts.join(' > ');
    }

    function textOf(el) {
        return (el.innerText || el.textContent || el.value || el.getAttribute('aria-label') || '').trim().substring(0,80);
    }

    function pushEvent(obj) {
        obj.ts = Date.now();
        obj.url = location.href;
        window.__bugula_events__.push(obj);
    }

    document.addEventListener('click', function (e) {
        const el = e.target.closest('a,button,[role="button"],[role="tab"],[role="menuitem"],input[type="submit"],input[type="button"],input[type="checkbox"],input[type="radio"]') || e.target;
        pushEvent({ type: 'click', selector: bestSelector(el), text: textOf(el), href: el.href || '', tag: el.tagName.toLowerCase() });
    }, true);

    document.addEventListener('change', function (e) {
        const el = e.target;
        const tag = el.tagName.toLowerCase();
        if (!['input','select','textarea'].includes(tag)) return;
        const inputType = (el.type || '').toLowerCase();
        if (['submit','button','reset','image'].includes(inputType)) return;
        let value = el.value || '';
        if (inputType === 'password') value = '***';
        pushEvent({ type: 'input', selector: bestSelector(el), text: el.placeholder || el.getAttribute('aria-label') || el.name || '', value: value, inputType: inputType });
    }, true);

    document.addEventListener('mouseup', function (e) {
        var sel = window.getSelection();
        var text = sel ? sel.toString().trim() : '';
        if (!text || text.length < 3) return;
        var el = (sel.anchorNode && sel.anchorNode.parentElement) ? sel.anchorNode.parentElement : e.target;
        pushEvent({ type: 'assert_text', text: text.substring(0, 200), selector: bestSelector(el) });
    }, true);

    document.addEventListener('keydown', function (e) {
        if (!['Enter','Tab'].includes(e.key)) return;
        const el = e.target;
        if (!['input','textarea'].includes(el.tagName.toLowerCase())) return;
        pushEvent({ type: 'key', selector: bestSelector(el), key: e.key.toLowerCase() });
    }, true);

    const _push = history.pushState.bind(history);
    history.pushState = function(state, title, url) {
        _push(state, title, url);
        pushEvent({ type: 'navigate', href: location.href });
    };
    window.addEventListener('popstate', function() {
        pushEvent({ type: 'navigate', href: location.href });
    });
})();
"""

_POLL_JS = r"""
var evts = window.__bugula_events__ || [];
window.__bugula_events__ = [];
return evts;
"""

_REINJECT_JS = r"""
window.__bugula_recorder_active__ = false;
""" + _RECORDER_JS

_MIN_WAIT_MS = 1500
_MAX_WAIT_MS = 8000


def _clean_selector(sel: str) -> str:
    return sel.strip()


def _events_to_steps(events: list[dict], source_url: str, no_wait: bool = False) -> list[dict]:
    steps: list[dict] = []
    last_url = source_url
    last_ts: int | None = None
    step_url = source_url

    i = 0
    while i < len(events):
        ev = events[i]
        ev_type = ev.get("type", "")
        ev_url  = ev.get("url", last_url)
        ev_ts   = ev.get("ts")

        if not no_wait and last_ts is not None and ev_ts is not None:
            gap_ms = ev_ts - last_ts
            if gap_ms > _MIN_WAIT_MS:
                wait_s = round(min(gap_ms, _MAX_WAIT_MS) / 1000, 1)
                steps.append({
                    "method": "wait", "url": "", "source_url": "",
                    "description": f"Wait {wait_s}s", "selector": "",
                    "element_text": "", "input_value": str(wait_s),
                    "submit_key": "",
                })
        last_ts = ev_ts

        if ev_type == "navigate":
            href = ev.get("href", "")
            if href and href != last_url:
                last_url = href
                step_url = href
                steps.append({
                    "method": "link", "url": href, "source_url": "",
                    "description": f"Open URL: {href}", "selector": "",
                    "element_text": "", "input_value": "", "submit_key": "",
                })
            i += 1
            continue

        nav_source = ev_url if ev_url != step_url else ""
        if ev_url:
            step_url = ev_url

        if ev_type == "input":
            submit_key = ""
            if i + 1 < len(events) and events[i + 1].get("type") == "key":
                submit_key = events[i + 1].get("key", "")
                i += 1
            value = ev.get("value", "")
            if value == "***":
                value = ""
            steps.append({
                "method": "form_input", "url": "", "source_url": nav_source,
                "description": f"Input: {ev.get('text','') or ev.get('selector','')}",
                "selector": _clean_selector(ev.get("selector", "")),
                "element_text": "", "input_value": value, "submit_key": submit_key,
            })
            i += 1
            continue

        if ev_type == "assert_text":
            text = ev.get("text", "")
            if text:
                steps.append({
                    "method": "assert_text", "url": "", "source_url": nav_source,
                    "description": f"Assert text: '{text[:40]}'",
                    "selector": "", "element_text": "",
                    "input_value": text, "submit_key": "",
                })
            i += 1
            continue

        if ev_type == "click":
            href = ev.get("href", "")
            tag  = ev.get("tag", "")
            text = ev.get("text", "")
            selector = _clean_selector(ev.get("selector", ""))
            if tag == "a" and href and not href.startswith("javascript"):
                steps.append({
                    "method": "link", "url": href, "source_url": "",
                    "description": f"Click link: {text or href}",
                    "selector": selector, "element_text": text,
                    "input_value": "", "submit_key": "",
                })
            else:
                steps.append({
                    "method": "click", "url": "", "source_url": nav_source,
                    "description": f"Click: {text or selector}",
                    "selector": selector, "element_text": text,
                    "input_value": "", "submit_key": "",
                })
            i += 1
            continue

        i += 1

    return steps


def _deduplicate(steps: list[dict]) -> list[dict]:
    out: list[dict] = []
    for s in steps:
        if out and out[-1] == s:
            continue
        if (out and s.get("method") == "link"
                and out[-1].get("method") == "link"
                and s.get("url") == out[-1].get("url")):
            continue
        out.append(s)
    return out


class SessionRecorder:
    """Wraps a Selenium driver and records user interactions."""

    POLL_INTERVAL = 0.8

    def __init__(self, driver, start_url: str):
        self.driver     = driver
        self.start_url  = start_url
        self._events: list[dict] = []
        self._running   = False
        self._last_url  = ""
        self._poll_thread: Optional[object] = None

    def start(self):
        self._running  = True
        self._last_url = ""
        self._events.clear()
        self._inject()
        import threading
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        log.info("Recorder started")

    def stop(self):
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=3)
        self._poll_once()
        log.info(f"Recorder stopped â€“ {len(self._events)} events captured")

    def _inject(self):
        try:
            self.driver.execute_script(_REINJECT_JS)
        except Exception as e:
            log.warning(f"Recorder inject failed: {e}")

    def _poll_once(self):
        try:
            current_url = self.driver.current_url
            if current_url != self._last_url:
                if self._last_url:
                    self._events.append({
                        "type": "navigate",
                        "url": self._last_url,
                        "href": current_url,
                        "ts": int(time.time() * 1000),
                    })
                self._last_url = current_url
                self._inject()
            raw = self.driver.execute_script(_POLL_JS) or []
            self._events.extend(raw)
        except Exception:
            pass

    def _poll_loop(self):
        while self._running:
            self._poll_once()
            time.sleep(self.POLL_INTERVAL)

    def to_yaml(self, name: str = "recording", url: str = "",
                browser: str = "chrome",
                username: str = "", password: str = "",
                no_wait: bool = False) -> str:
        steps = _events_to_steps(self._events, url or self.start_url, no_wait=no_wait)
        steps = _deduplicate(steps)
        meta: dict = {"url": url or self.start_url}
        if browser and browser != "chrome":
            meta["browser"] = browser
        if username:
            meta["username"] = username
        if password:
            meta["password"] = password
        doc = {"meta": meta, "testcases": steps}
        return yaml.dump(doc, allow_unicode=True,
                         default_flow_style=False, sort_keys=False)

    def event_count(self) -> int:
        return len(self._events)

