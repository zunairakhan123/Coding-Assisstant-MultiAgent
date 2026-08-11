import posixpath
import base64
from pydantic import BaseModel, Field
from typing import Literal
from src.sandbox.manager import SandboxManager
from src.core.exceptions import SecurityViolationError
from src.core.logger import logger
from src.agents.coder.state import CoderAction
import re

class Harness:
    """Gatekeeper for state-changing actions. Validates and executes safely."""
    
    def __init__(self, sandbox: SandboxManager):
        self.sandbox = sandbox
        self.workspace_root = "/workspace"
        self.log = logger.bind(component="harness", task_id=sandbox.task_id)

    def _is_valid_filename(self, filepath: str) -> bool:
        """Checks if the filepath contains invalid characters for Windows/Linux."""
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
    
    def apply_action(self, action: CoderAction) -> bool:
        """Validates and applies the structural change to the sandbox."""
        if action.action == "finish":
            return True
    
        if not action.file_path:
            self.log.error("missing_file_path", action=action.action)
            raise ValueError(f"A valid file_path is required for '{action.action}' actions.")

        safe_path = self._validate_path(action.file_path)
        
        if action.action in ["write", "edit"]:
            dir_name = posixpath.dirname(safe_path)
            if dir_name:
                self.sandbox.execute(f"mkdir -p '{dir_name}'")
                
        if action.action == "write":
            encoded_content = base64.b64encode(action.content.encode('utf-8')).decode('utf-8')
            cmd = f"echo '{encoded_content}' | base64 -d > '{safe_path}'"
            
            res = self.sandbox.execute(cmd)
            if res.status != "success":
                self.log.error("write_failed", file=safe_path, stderr=res.stderr)
                raise Exception(f"Failed to write file {safe_path}: {res.stderr}")
                
            self.log.info("patch_applied", action=action.action, file=safe_path)
            return True
            
        elif action.action == "edit":
            if not action.search_block or action.replace_block is None:
                raise ValueError("Both 'search_block' and 'replace_block' are required for edits.")
            
            res = self.sandbox.execute(f"cat '{safe_path}'")
            if res.exit_code != 0:
                raise ValueError(f"Cannot edit {safe_path}, file does not exist. Use 'write' instead.")
            
            current_content = res.stdout
            
            if action.search_block not in current_content:
                self.log.warning("search_block_not_found", search_preview=action.search_block[:50])
                raise ValueError("The exact `search_block` was not found in the file. You must match indentation and newlines perfectly.")
            
            new_content = current_content.replace(action.search_block, action.replace_block, 1)
            encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            
            res = self.sandbox.execute(f"echo '{encoded_content}' | base64 -d > '{safe_path}'")
            if res.status != "success":
                raise Exception(f"Failed to edit file {safe_path}: {res.stderr}")
                
            self.log.info("surgical_edit_applied", file=safe_path)
            return True
            
        elif action.action == "delete":
            res = self.sandbox.execute(f"rm '{safe_path}'")
            if res.status != "success":
                 raise Exception(f"Failed to delete file {safe_path}: {res.stderr}")
            return True
            
        return False

    def validate_command(self, command: str) -> bool:
        """Ensures the LLM isn't trying to run malicious commands."""
        if not command:
            return False
            
        if any(char in command for char in [";", "&&", "||", "|", ">", "<"]):
            self.log.error("security_violation", command=command, reason="chained_command")
            raise SecurityViolationError(f"Forbidden command structure: {command}")
            
        forbidden_binaries = ["curl ", "wget ", "nc ", "ping ", "ssh ", "apt-get ", "apk "]
        for f in forbidden_binaries:
            if command.strip().startswith(f.strip()):
                self.log.error("security_violation", command=command, reason="forbidden_binary")
                raise SecurityViolationError(f"Forbidden binary requested: {command}")
                
        return True