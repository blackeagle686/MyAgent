import os
from typing import Any
from .base import BaseTool
from .code_security_decorator import safe_execution, restrict_path, audit_log


class FileReadTool(BaseTool):
    name = "read_file"
    description = "Reads the contents of a local file. Provide 'path' string argument."
    
    @safe_execution
    @restrict_path
    @audit_log
    def execute(self, path: str, **kwargs) -> Any:
        if not os.path.exists(path):
            return f"Error: File not found at path '{path}'"
        if not os.path.isfile(path):
            return f"Error: Path '{path}' is not a file."
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"File content of {path}:\n\n{content}"
        except Exception as e:
            return f"Failed to read file: {e}"


class FileWriteTool(BaseTool):
    name = "write_file"
    description = "Writes content to a local file. Provide 'path' and 'content' string arguments."
    
    @safe_execution
    @restrict_path
    @audit_log
    def execute(self, path: str, content: str, **kwargs) -> Any:
        try:
            # Create directories if they don't exist
            dir_path = os.path.dirname(os.path.abspath(path))
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Failed to write file: {e}"


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "Lists files and folders in a local directory. Provide 'path' string argument."
    
    @safe_execution
    @restrict_path
    @audit_log
    def execute(self, path: str, **kwargs) -> Any:
        if not os.path.exists(path):
            return f"Error: Directory not found at path '{path}'"
        if not os.path.isdir(path):
            return f"Error: Path '{path}' is not a directory."
            
        try:
            items = os.listdir(path)
            if not items:
                return f"Directory '{path}' is empty."
            return f"Contents of {path}:\n" + "\n".join(f"- {i}" for i in items)
        except Exception as e:
            return f"Failed to list directory: {e}"


class FileDeleteTool(BaseTool):
    """Safely delete a file within the workspace."""
    name = "delete_file"
    description = "Deletes a file. Provide 'path' string argument."
    
    @safe_execution
    @restrict_path
    @audit_log
    def execute(self, path: str, **kwargs) -> Any:
        if not os.path.exists(path):
            return f"Error: File not found at path '{path}'"
        if not os.path.isfile(path):
            return f"Error: Path '{path}' is not a file."
        try:
            os.remove(path)
            return f"Successfully deleted file: {path}"
        except Exception as e:
            return f"Failed to delete file: {e}"


class CreateDirTool(BaseTool):
    """Safely create a directory within the workspace."""
    name = "create_dir"
    description = "Creates a directory. Provide 'path' string argument."
    
    @safe_execution
    @restrict_path
    @audit_log
    def execute(self, path: str, **kwargs) -> Any:
        try:
            os.makedirs(path, exist_ok=True)
            return f"Successfully created directory: {path}"
        except Exception as e:
            return f"Failed to create directory: {e}"
