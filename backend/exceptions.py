"""
exceptions.py
-------------
SOUL's list of problems, each with a friendly message.
Other files use it like this:

    from backend.exceptions import AIQuotaError
    raise AIQuotaError()
"""


class SoulError(Exception):
    """The parent of all SOUL problems."""

    status_code = 500
    error_code = "soul_error"
    default_message = "Something went wrong inside SOUL."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class ConfigurationError(SoulError):
    status_code = 500
    error_code = "configuration_error"
    default_message = "SOUL is not set up correctly. Check your .env file."


class AIAuthError(SoulError):
    status_code = 500
    error_code = "ai_auth_error"
    default_message = (
        "The OpenAI API key was rejected. Check that OPENAI_API_KEY in your "
        ".env file is correct, then restart SOUL."
    )


class AIQuotaError(SoulError):
    status_code = 402
    error_code = "ai_quota_exceeded"
    default_message = (
        "The AI account has no credit left, or its free limit is used up. "
        "Wait a while and try again, or check your AI provider's billing page."
    )


class AIRateLimitError(SoulError):
    status_code = 429
    error_code = "ai_rate_limited"
    default_message = "SOUL is sending too many requests. Please wait a moment and try again."


class AITimeoutError(SoulError):
    status_code = 504
    error_code = "ai_timeout"
    default_message = "The AI took too long to answer. Please try again."


class AIConnectionError(SoulError):
    status_code = 503
    error_code = "ai_connection_error"
    default_message = "SOUL could not reach the AI. Check your internet connection."


class AIModelError(SoulError):
    status_code = 500
    error_code = "ai_model_error"
    default_message = (
        "The AI model name is not available. Check OPENAI_MODEL in your .env file."
    )


class AIServiceError(SoulError):
    status_code = 502
    error_code = "ai_service_error"
    default_message = "The AI service had a problem. Please try again in a moment."


def translate_openai_error(error: Exception) -> SoulError:
    """
    Turn a scary OpenAI error into one of SOUL's friendly errors.
    If we do not recognise it, we return a general friendly error.
    """
    import openai  # imported here so this file stays light

    # Already one of ours? Keep it.
    if isinstance(error, SoulError):
        return error

    # Timeout must be checked BEFORE connection error
    if isinstance(error, openai.APITimeoutError):
        return AITimeoutError()

    if isinstance(error, openai.APIConnectionError):
        return AIConnectionError()

    if isinstance(error, openai.AuthenticationError):
        return AIAuthError()

    if isinstance(error, openai.RateLimitError):
        # OpenAI uses the same error for "too fast" and "no credit".
        # So we also read the message to tell them apart.
        code = str(getattr(error, "code", "") or "").lower()
        text = str(error).lower()
        if (
            code == "insufficient_quota"
            or "credit" in text
            or "quota" in text
            or "billing" in text
        ):
            return AIQuotaError()
        return AIRateLimitError()

    if isinstance(error, openai.NotFoundError):
        return AIModelError()

    if isinstance(error, openai.APIError):
        return AIServiceError()

    return AIServiceError()