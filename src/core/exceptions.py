class CodingAssistantError(Exception):
    """Base exception for all domain errors."""
    pass

class SandboxError(CodingAssistantError):
    """Raised when the sandbox fails to provision, execute, or cleanup."""
    pass

class ExecutionTimeoutError(SandboxError):
    """Raised specifically when a command times out inside the sandbox."""
    pass

class SecurityViolationError(CodingAssistantError):
    """Raised when a path or command violates the Harness policy."""
    pass