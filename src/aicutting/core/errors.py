class AiCuttingError(Exception):
    """Base exception for expected AiCutting failures."""


class ValidationError(AiCuttingError):
    """Raised when user input or environment validation fails."""


class ExternalToolError(AiCuttingError):
    """Raised when FFmpeg, ffprobe, Resolve, or another external tool fails."""
