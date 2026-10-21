from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Błąd reguły biznesowej mapowany na odpowiedź HTTP z czytelnym komunikatem."""

    status_code = 400

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code  # stabilny identyfikator dla klienta, niezależny od treści komunikatu


class NotFound(DomainError):
    status_code = 404


class Forbidden(DomainError):
    status_code = 403


class Conflict(DomainError):
    status_code = 409


class Unauthorized(DomainError):
    status_code = 401


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        headers = (
            {"Retry-After": str(exc.retry_after)} if isinstance(exc, TooManyRequests) else None
        )
        content = {"detail": exc.message} | ({"code": exc.code} if exc.code else {})
        return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


class TooManyRequests(DomainError):
    status_code = 429

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after
