from src.agents.coder.state import StructuredError

class ErrorParser:
    """Extracts compact, meaningful error contexts from raw sandbox tracebacks."""
    
    @staticmethod
    def parse(stderr: str, filepath: str) -> StructuredError:
        # Standardize the error string
        raw_error = stderr.strip() if stderr else "Unknown Sandbox Error"
        lines = raw_error.split('\n')
        
        error_type = "ExecutionError"
        message = lines[-1] if lines else raw_error
        
        # Python tracebacks usually end with "ExceptionType: detail message"
        if ":" in message:
            error_type = message.split(":")[0].strip()

        # Keep the last 2000 characters to prevent context-window bloat
        compact_traceback = raw_error[-2000:] if len(raw_error) > 2000 else raw_error

        return StructuredError(
            error_type=error_type,
            message=message,
            file=filepath,
            traceback=compact_traceback
        )