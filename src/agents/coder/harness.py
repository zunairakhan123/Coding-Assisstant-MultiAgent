import posixpath
import base64
from pydantic import BaseModel, Field
from typing import Literal
from src.sandbox.manager import SandboxManager
from src.core.exceptions import SecurityViolationError
from src.core.logger import logger
import re

class PatchAction(BaseModel):
    """The structured output schema the LLM will eventually generate."""
    action: Literal["write", "edit", "delete"] = Field(
        description="The type of operation to perform."
    )
    file_path: str = Field(
        description="The relative path to the file in the workspace (e.g., 'app/main.py')."
    )
    content: str = Field(
        default="", 
        description="The full code content to write. Required for 'write' and 'edit'."
    )

class Harness:
    """Gatekeeper for state-changing actions. Validates and executes safely."""
    
    def __init__(self, sandbox: SandboxManager):
        self.sandbox = sandbox
        self.workspace_root = "/workspace"
        self.log = logger.bind(component="harness", task_id=sandbox.task_id)

    def _is_valid_filename(self, filepath: str) -> bool:
        """NEW: Checks if the filepath contains invalid characters for Windows/Linux."""
        # Reject newlines, tabs, and common illegal characters
        if re.search(r"[\n\r\t<>:\"|?*!]", filepath):
            return False
        return True

    def _validate_path(self, filepath: str) -> str:
        """Ensures the path is valid and cannot traverse outside the workspace."""
        if not self._is_valid_filename(filepath):
            self.log.error("security_violation_filename", attempted_path=filepath)
            raise SecurityViolationError(f"Invalid characters in filename: {filepath}")

        clean_path = posixpath.normpath(posixpath.join(self.workspace_root, filepath))
        
        if not clean_path.startswith(self.workspace_root):
            self.log.error("security_violation_traversal", attempted_path=filepath)
            raise SecurityViolationError(f"Path traversal detected: {filepath}")
            
        return posixpath.relpath(clean_path, self.workspace_root)
    
    def apply_action(self, patch: PatchAction) -> bool:
        """Validates and applies the structural change to the sandbox."""
        safe_path = self._validate_path(patch.file_path)
        
        if patch.action in ["write", "edit"]:
            # Ensure the directory exists before writing the file
            dir_name = posixpath.dirname(safe_path)
            if dir_name:
                self.sandbox.execute(f"mkdir -p '{dir_name}'")
                
            # Base64 encoding bypasses all shell quoting and formatting issues
            encoded_content = base64.b64encode(patch.content.encode('utf-8')).decode('utf-8')
            cmd = f"echo '{encoded_content}' | base64 -d > '{safe_path}'"
            
            res = self.sandbox.execute(cmd)
            if res.status != "success":
                self.log.error("patch_application_failed", file=safe_path, stderr=res.stderr)
                raise Exception(f"Failed to write file {safe_path}: {res.stderr}")
                
            self.log.info("patch_applied", action=patch.action, file=safe_path)
            return True
            
        elif patch.action == "delete":
            res = self.sandbox.execute(f"rm '{safe_path}'")
            if res.status != "success":
                 raise Exception(f"Failed to delete file {safe_path}: {res.stderr}")
            return True
            
        return False

    def validate_command(self, command: str) -> bool:
        """Ensures the LLM isn't trying to run malicious commands."""
        if not command:
            return False
            
        # Prevent chaining commands (e.g., 'pip install fastapi; rm -rf /')
        if any(char in command for char in [";", "&&", "||", "|", ">", "<"]):
            self.log.error("security_violation", command=command, reason="chained_command")
            raise SecurityViolationError(f"Forbidden command structure: {command}")
            
        # Explicit blocklist for network/exfiltration tools, but allow 'pip'
        forbidden_binaries = ["curl ", "wget ", "nc ", "ping ", "ssh ", "apt-get ", "apk "]
        for f in forbidden_binaries:
            if command.strip().startswith(f.strip()):
                self.log.error("security_violation", command=command, reason="forbidden_binary")
                raise SecurityViolationError(f"Forbidden binary requested: {command}")
                
        return True