"""
Custom exception classes and error handlers.

Implements RFC 7807 Problem Details for HTTP APIs standard.
"""
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response model."""
    type: str
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        title: Optional[str] = None,
        type_uri: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.title = title or self._get_default_title(status_code)
        self.type_uri = type_uri or f"https://bakalr.cms/errors/{status_code}"
        self.errors = errors
        super().__init__(detail)
    
    @staticmethod
    def _get_default_title(status_code: int) -> str:
        """Get default title based on status code."""
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        return titles.get(status_code, "Error")


class BadRequestException(AppException):
    """400 Bad Request."""
    def __init__(self, detail: str = "Bad request", errors: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, errors=errors)


class UnauthorizedException(AppException):
    """401 Unauthorized."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class ForbiddenException(AppException):
    """403 Forbidden."""
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class NotFoundException(AppException):
    """404 Not Found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class ConflictException(AppException):
    """409 Conflict."""
    def __init__(self, detail: str = "Resource conflict", errors: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_409_CONFLICT, detail, errors=errors)


class ValidationException(AppException):
    """422 Unprocessable Entity."""
    def __init__(self, detail: str = "Validation failed", errors: Optional[Dict[str, Any]] = None):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail, errors=errors)


class RateLimitException(AppException):
    """429 Too Many Requests."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, detail)


class InternalServerException(AppException):
    """500 Internal Server Error."""
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


# Exception handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    problem = ProblemDetail(
        type=exc.type_uri,
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url),
        errors=exc.errors,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with RFC 7807 format."""
    problem = ProblemDetail(
        type=f"https://bakalr.cms/errors/{exc.status_code}",
        title=AppException._get_default_title(exc.status_code),
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with RFC 7807 format."""
    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        if field in errors:
            if isinstance(errors[field], list):
                errors[field].append(error["msg"])
            else:
                errors[field] = [errors[field], error["msg"]]
        else:
            errors[field] = error["msg"]
    
    problem = ProblemDetail(
        type="https://bakalr.cms/errors/validation",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="One or more validation errors occurred",
        instance=str(request.url),
        errors=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    # Log the exception for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception", exc_info=exc)
    
    problem = ProblemDetail(
        type="https://bakalr.cms/errors/500",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(exclude_none=True),
    )
