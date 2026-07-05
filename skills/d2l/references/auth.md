# d2l auth flow

D2L tokens expire about hourly. Check status first:

```bash
d2l token
```

If expired or invalid, try saved-session refresh:

```bash
d2l login --headless
```

If that fails, ask the user whether you may launch browser login. If they agree:

```bash
d2l login
```

The browser is only for authentication. Do not scrape course data through browser automation, page JavaScript, or network-panel copying except for explicit manual setup directed by the user.

After auth:

```bash
d2l token
d2l whoami
d2l --md courses
```
