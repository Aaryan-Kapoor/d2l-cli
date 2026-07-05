# d2l auth flow

D2L tokens expire about hourly, but every `d2l` command auto-refreshes the
token in the background using the saved browser session — auth normally
maintains itself after the first login.

Check status any time:

```bash
d2l token
```

If a command fails with a sign-in error, the saved browser session has fully
expired. Ask the user whether you may launch browser login; if they agree:

```bash
d2l login
```

`d2l login` launches Playwright's bundled Chromium when available and
automatically falls back to installed Google Chrome or Microsoft Edge, so it
works without `playwright install chromium` on most machines. Pin a browser
with `--channel chrome|msedge|chromium` if needed. Set `D2L_NO_AUTO_LOGIN=1`
to disable the automatic background refresh.

The browser is only for authentication. Do not scrape course data through
browser automation, page JavaScript, or network-panel copying.

After auth:

```bash
d2l token
d2l whoami
d2l --md courses
```
