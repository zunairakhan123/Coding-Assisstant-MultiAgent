import time
import os
import tarfile
import io
import docker
from docker.errors import DockerException
from src.core.config import settings
from src.core.exceptions import SandboxError, ExecutionTimeoutError
from src.core.logger import logger
from src.sandbox.models import ExecutionResult

class SandboxManager:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.client = docker.from_env()
        self.container = None
        self.log = logger.bind(task_id=self.task_id)

    def _ensure_secure_image(self) -> str:
        """Dynamically builds a secure, non-root Docker image if it doesn't exist."""
        image_tag = "coding-assistant-sandbox:latest"
        try:
            self.client.images.get(image_tag)
        except docker.errors.ImageNotFound:
            self.log.info("building_secure_sandbox_image", tag=image_tag)
            dockerfile = """
            FROM python:3.11-slim
            # Create a non-root user 'coder' with UID 1000
            RUN useradd -m -u 1000 coder && \
                mkdir -p /workspace && \
                chown -R coder:coder /workspace
            USER coder
            WORKDIR /workspace
            """
            f = io.BytesIO(dockerfile.encode('utf-8'))
            self.client.images.build(fileobj=f, rm=True, tag=image_tag)
            self.log.info("secure_sandbox_image_built")
        return image_tag

    def start(self):
        """Provisions the sandbox, or attaches if it already exists."""
        # 1. Check if the container is already running from a previous loop
        try:
            self.container = self.client.containers.get(f"sandbox_{self.task_id}")
            self.log = self.log.bind(container_id=self.container.id[:12])
            self.log.info("sandbox_already_running_attached")
            return  # Exit early, we are good to go!
        except docker.errors.NotFound:
            pass  # Container does not exist, proceed to create it

        # 2. Provision new container
        try:
            secure_image = self._ensure_secure_image()
            self.log.info("provisioning_sandbox", image=secure_image)
            
            self.container = self.client.containers.run(
                image=secure_image,
                command="tail -f /dev/null", 
                detach=True,
                mem_limit=settings.SANDBOX_MEM_LIMIT,
                cpu_quota=settings.SANDBOX_CPU_QUOTA,
                working_dir="/workspace",
                name=f"sandbox_{self.task_id}",
                remove=True,
                user="1000:1000",             
                security_opt=["no-new-privileges:true"], 
                cap_drop=["ALL"]              
            )
            self.log = self.log.bind(container_id=self.container.id[:12])
            self.log.info("sandbox_provisioned")
        except DockerException as e:
            self.log.error("sandbox_provision_failed", error=str(e))
            raise SandboxError(f"Failed to start sandbox: {e}")

    def execute(self, command: str, timeout: int = settings.EXECUTION_TIMEOUT_SECONDS) -> ExecutionResult:
        """Executes a command inside the sandbox deterministically."""
        if not self.container:
            raise SandboxError("Sandbox is not running.")

        start_time = time.time()
        
        # Enforce timeout using Linux 'timeout' utility inside the container
        safe_command = f"timeout {timeout}s {command}"
        
        try:
            self.log.info("executing_command", command=command)
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", safe_command],
                workdir="/workspace",
                demux=True # Separates stdout and stderr tuples
            )
            
            stdout_bytes, stderr_bytes = output if output else (b"", b"")
            stdout_str = stdout_bytes.decode("utf-8") if stdout_bytes else ""
            stderr_str = stderr_bytes.decode("utf-8") if stderr_bytes else ""
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # exit code 124 is the standard standard linux timeout exit code
            if exit_code == 124:
                status = "timeout"
            elif exit_code == 0:
                status = "success"
            else:
                status = "error"

            result = ExecutionResult(
                status=status,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                command=command
            )
            
            self.log.info("execution_complete", status=status, exit_code=exit_code, duration_ms=duration_ms)
            return result

        except DockerException as e:
            self.log.error("execution_failed", error=str(e))
            raise SandboxError(f"Execution failed: {e}")

    def cleanup(self):
        """Forcefully destroys the container."""
        if self.container:
            try:
                self.log.info("cleaning_up_sandbox")
                self.container.stop(timeout=1)
                self.log.info("sandbox_destroyed")
            except DockerException as e:
                self.log.error("cleanup_failed", error=str(e))
            finally:
                self.container = None
                
    def connect(self):
        """Attaches to an existing running sandbox for this task."""
        try:
            self.container = self.client.containers.get(f"sandbox_{self.task_id}")
            self.log = self.log.bind(container_id=self.container.id[:12])
            self.log.info("attached_to_existing_sandbox")
        except docker.errors.NotFound:
            self.log.error("sandbox_not_found", name=f"sandbox_{self.task_id}")
            raise SandboxError("Sandbox container not found. Did it crash?")
    
    def export_workspace(self, host_dest_dir: str):
        """
        Exports the container's /workspace directory to the host machine.
        Must be called BEFORE cleanup().
        """
        if not self.container:
            self.log.error("export_failed", reason="No container running")
            return

        self.log.info("exporting_workspace", destination=host_dest_dir)
        try:
            # Docker SDK get_archive returns a tuple: (stream_generator, stat_dict)
            bits, stat = self.container.get_archive("/workspace")
            
            # Read the raw tar stream into memory
            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)
            
            # Ensure the host destination directory exists
            os.makedirs(host_dest_dir, exist_ok=True)
            
            # Extract the tarball to the host
            with tarfile.open(fileobj=tar_stream) as tar:
                tar.extractall(path=host_dest_dir)
                
            self.log.info("workspace_exported_successfully")
            
        except Exception as e:
            self.log.error("workspace_export_failed", error=str(e))
