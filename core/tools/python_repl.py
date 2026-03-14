from typing import Any
import sys
import io
import contextlib
from .base import BaseTool
from .code_security_decorator import safe_execution, validate_code, timeout, audit_log


class PythonREPLTool(BaseTool):
    """
    Executes Python code in a local runtime with security restrictions.
    WARNING: This executes code. Use with caution in an insecure environment.
    """
    name = "python_repl"
    description = (
        "Executes python code and returns stdout and stderr. "
        "Provide code as a string in the 'code' argument. "
        "Use this for math, processing data, or scripts."
    )
    
    @safe_execution
    @validate_code
    @timeout(seconds=10)
    @audit_log
    def execute(self, code: str, **kwargs) -> Any:
        try:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                # Exec block with its own globals/locals to prevent scope contamination
                # We provide a restricted set of safe builtins
                safe_globals = {
                    "__builtins__": {
                        "len": len,
                        "range": range,
                        "str": str,
                        "int": int,
                        "float": float,
                        "list": list,
                        "dict": dict,
                        "tuple": tuple,
                        "set": set,
                        "bool": bool,
                        "sum": sum,
                        "max": max,
                        "min": min,
                        "abs": abs,
                        "print": print,
                        "sorted": sorted,
                        "enumerate": enumerate,
                        "zip": zip,
                        "map": map,
                        "filter": filter,
                        "any": any,
                        "all": all,
                    }
                }
                exec(code, safe_globals)
                
            out_str = stdout.getvalue()
            err_str = stderr.getvalue()
            
            result = ""
            if out_str:
                result += f"STDOUT:\n{out_str}\n"
            if err_str:
                result += f"STDERR:\n{err_str}\n"
                
            return result.strip() or "Code executed successfully (no output)."
        except Exception as e:
            return f"Error executing code: {type(e).__name__}: {str(e)}"

