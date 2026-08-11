from src.sandbox.manager import SandboxManager
from src.core.logger import logger

class ContextEngine:
    """Extracts stateful context from the Sandbox safely."""
    
    def __init__(self, sandbox: SandboxManager):
        self.sandbox = sandbox
        self.log = logger.bind(component="context_engine", task_id=sandbox.task_id)

    def get_directory_tree(self) -> list[str]:
        """Returns a flat list of file paths in the workspace, ignoring hidden files."""
        # find files, not directories, ignore paths containing '/.' 
        cmd = "find . -type f -not -path '*/\\.*' | sort"
        res = self.sandbox.execute(cmd)
        
        if res.status == "success":
            lines = res.stdout.strip().split('\n')
            # Remove the leading './' from find output
            return [line.removeprefix('./') for line in lines if line]
        
        self.log.warning("tree_fetch_failed", stderr=res.stderr)
        return []

    def read_file(self, filepath: str) -> str:
        """Reads a file from the sandbox."""
        cmd = f"cat '{filepath}'"
        res = self.sandbox.execute(cmd)
        
        if res.status == "success":
            return res.stdout
            
        self.log.error("file_read_failed", file=filepath, stderr=res.stderr)
        return f"<Error reading file {filepath}: {res.stderr}>"