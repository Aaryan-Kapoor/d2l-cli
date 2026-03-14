import functools
import click


class D2LError(Exception):
    pass


class TokenExpiredError(D2LError):
    pass


class TokenNotFoundError(D2LError):
    pass


class APIError(D2LError):
    def __init__(self, status_code, url, body=""):
        self.status_code = status_code
        self.url = url
        self.body = body
        super().__init__(f"HTTP {status_code}: {url}")


class RateLimitError(APIError):
    def __init__(self, url, retry_after=None):
        self.retry_after = retry_after
        super().__init__(429, url, "")


class ForbiddenError(APIError):
    pass


class NotFoundError(APIError):
    pass


def raise_for_status(response):
    """Map HTTP errors to typed exceptions."""
    if response.ok:
        return
    url = response.url
    body = response.text[:300]
    code = response.status_code
    if code == 401:
        raise TokenExpiredError("Token expired or invalid. Run: d2l login")
    elif code == 403:
        raise ForbiddenError(code, url, body)
    elif code == 404:
        raise NotFoundError(code, url, body)
    elif code == 429:
        retry = response.headers.get("Retry-After")
        raise RateLimitError(url, int(retry) if retry else None)
    else:
        raise APIError(code, url, body)


def handle_errors(fn):
    """Decorator that catches D2L exceptions and prints clean CLI messages."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TokenNotFoundError:
            click.echo("No token found. Run: d2l login", err=True)
            raise SystemExit(1)
        except TokenExpiredError as e:
            click.echo(f"Token expired. Run: d2l login", err=True)
            raise SystemExit(1)
        except RateLimitError as e:
            msg = f"Rate limited by D2L."
            if e.retry_after:
                msg += f" Retry after {e.retry_after}s."
            click.echo(msg, err=True)
            raise SystemExit(1)
        except ForbiddenError as e:
            click.echo(f"Access denied: {e.url}", err=True)
            raise SystemExit(1)
        except NotFoundError as e:
            click.echo(f"Not found: {e.url}", err=True)
            raise SystemExit(1)
        except APIError as e:
            click.echo(f"API error ({e.status_code}): {e}", err=True)
            raise SystemExit(1)
        except D2LError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
    return wrapper
