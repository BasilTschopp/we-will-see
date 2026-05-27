import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models.models import log


def _cfg():
    from adapters.crypto import get_email_setting
    return {
        "enabled":        get_email_setting("email_enabled",        "0") == "1",
        "automated_only": get_email_setting("email_automated_only", "0") == "1",
        "host":           get_email_setting("email_smtp_host",      ""),
        "port":           int(get_email_setting("email_smtp_port",  "587") or "587"),
        "user":           get_email_setting("email_smtp_user",      ""),
        "password":       get_email_setting("email_smtp_pass",      ""),
        "recipient":      get_email_setting("email_recipient",      ""),
        "use_ssl":        get_email_setting("email_use_ssl",        "0") == "1",
    }


def send_failure_alert(run_name: str, results, *, automated: bool = False) -> None:
    cfg = _cfg()
    if not cfg["enabled"]:
        log.info("Email alert: disabled.")
        return
    if cfg["automated_only"] and not automated:
        log.info("Email alert: skipped (only automated runs, this is a GUI run).")
        return
    if not cfg["host"] or not cfg["recipient"]:
        log.warning("Email alert: SMTP host or recipient not configured.")
        return

    failures = [r for r in results if r.status == "FEHLER"]
    if not failures:
        log.info("Email alert: no failures, nothing to send.")
        return

    log.info(f"Email alert: sending to {cfg['recipient']} — {len(failures)} failure(s).")

    ok_count  = sum(1 for r in results if r.status == "OK")
    err_count = len(failures)

    subject = f"Bugula: {err_count} error(s) – {run_name}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["user"] or "bugula@localhost"
    msg["To"]      = cfg["recipient"]
    msg.attach(MIMEText(_build_text(run_name, ok_count, err_count, failures), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(run_name, ok_count, err_count, failures), "html",  "utf-8"))

    try:
        ctx = ssl.create_default_context()
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx) as s:
                if cfg["user"] and cfg["password"]:
                    s.login(cfg["user"], cfg["password"])
                s.sendmail(msg["From"], cfg["recipient"], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
                s.ehlo()
                s.starttls(context=ctx)
                if cfg["user"] and cfg["password"]:
                    s.login(cfg["user"], cfg["password"])
                s.sendmail(msg["From"], cfg["recipient"], msg.as_string())
        log.info(f"Alert email sent to {cfg['recipient']} — {err_count} error(s) in '{run_name}'")
    except Exception as e:
        log.error(f"Failed to send alert email: {e}")


def test_connection() -> tuple[bool, str]:
    """Returns (success, message). Used by the settings UI."""
    cfg = _cfg()
    if not cfg["host"]:
        return False, "No SMTP host configured."
    try:
        ctx = ssl.create_default_context()
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx) as s:
                if cfg["user"] and cfg["password"]:
                    s.login(cfg["user"], cfg["password"])
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
                s.ehlo()
                s.starttls(context=ctx)
                if cfg["user"] and cfg["password"]:
                    s.login(cfg["user"], cfg["password"])
        return True, "Connection successful."
    except Exception as e:
        return False, str(e)


def _build_html(run_name, ok, err, failures) -> str:
    rows = ""
    for i, r in enumerate(failures):
        bg = "#ffffff" if i % 2 == 0 else "#f9f9f9"
        rows += (
            f"<tr style='background:{bg}'>"
            f"<td style='padding:12px 16px;border-bottom:1px solid #f0f0f0;"
            f"font-size:13px;color:#1d1d1f;white-space:nowrap'>{r.description or '–'}</td>"
            f"<td style='padding:12px 16px;border-bottom:1px solid #f0f0f0;"
            f"font-size:12px;color:#86868b;font-family:ui-monospace,monospace;"
            f"word-break:break-all'>{r.url or '–'}</td>"
            f"<td style='padding:12px 16px;border-bottom:1px solid #f0f0f0;"
            f"font-size:13px;color:#ff3b30'>{r.error_detail or '–'}</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7;padding:40px 0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

        <!-- Header -->
        <tr><td style="background:#ffffff;border-radius:18px 18px 0 0;padding:36px 40px 28px">
          <p style="margin:0 0 6px;font-size:13px;color:#86868b;letter-spacing:.5px;text-transform:uppercase">Bugula</p>
          <h1 style="margin:0;font-size:28px;font-weight:600;color:#1d1d1f;letter-spacing:-.5px">Test Run Failed</h1>
          <p style="margin:10px 0 0;font-size:15px;color:#86868b">{run_name}</p>
        </td></tr>

        <!-- Failures table -->
        <tr><td style="background:#ffffff;padding:0 40px 32px">
          <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:10px;overflow:hidden;border:1px solid #f0f0f0">
            <thead>
              <tr style="background:#f5f5f7">
                <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.5px">Test</th>
                <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.5px">URL</th>
                <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.5px">Error</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f5f5f7;border-radius:0 0 18px 18px;padding:20px 40px;text-align:center">
          <p style="margin:0;font-size:12px;color:#86868b">Sent by Bugula</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _build_text(run_name, ok, err, failures) -> str:
    lines = [
        "Bugula Test Alert",
        f"Run:    {run_name}",
        f"Result: {err} error(s), {ok} OK",
        "",
        "Failed tests:",
        "-" * 60,
    ]
    for r in failures:
        lines.append(f"  [{r.method}] {r.description}")
        lines.append(f"    URL:   {r.url or '–'}")
        lines.append(f"    Error: {r.error_detail or '–'}")
        lines.append("")
    return "\n".join(lines)
