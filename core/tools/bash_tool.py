import subprocess
from typing import Any
from .base import BaseTool
from .code_security_decorator import safe_execution, timeout, audit_log, restrict_path, validate_code

class BashExecuteTool(BaseTool):
    """
    Executes bash commands or scripts and returns the terminal output.
    """
    name = "bash_execute"
    description = (
        "Executes a bash command or script and returns stdout and stderr. "
        "Provide the command as a string in the 'code' argument. "
        "Use this for system operations, file searching, or directory listings."
    )

    @safe_execution
    @validate_code
    @timeout(seconds=30)
    @audit_log
    def execute(self, code: str, **kwargs) -> Any:
        try:
            # Execute the command using subprocess
            # shell=True is needed for complex bash scripts/pipes
            process = subprocess.run(
                code,
                shell=True,
                text=True,
                capture_output=True,
                check=False
            )
            
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            
            result = ""
            if stdout:
                result += f"STDOUT:\n{stdout}\n"
            if stderr:
                result += f"STDERR:\n{stderr}\n"
            
            return result.strip() or "Command executed successfully (no output)."
            
        except Exception as e:
            return f"Error executing bash command: {e}"
