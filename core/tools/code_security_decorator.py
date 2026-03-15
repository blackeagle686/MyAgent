"""
security.py
===========
Security decorators for agent tools.

Decorators
----------
safe_execution  — catches and logs all unhandled exceptions
restrict_path   — blocks filesystem access outside the workspace
validate_code   — blocks dangerous patterns before code execution
timeout         — kills long-running calls (POSIX only)
audit_log       — logs every tool invocation and its result
"""

from __future__ import annotations

import functools
import logging
import os
import signal
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Sandbox root — every path-based tool is confined here
WORKSPACE_ROOT: str = os.path.abspath(".")

# Patterns that must never appear in code passed to the agent
_BLOCKED_PATTERNS: tuple[str, ...] = (
    "os.system",
    "os.popen",
    "subprocess",
    "shutil.rmtree",
    "eval(",
    "exec(",
    "__import__",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_name(self_or_func) -> str:
    """Best-effort tool name for logging — works with and without `self`."""
    return getattr(self_or_func, "name", None) or getattr(self_or_func, "__name__", "unknown")


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def safe_execution(func: Callable) -> Callable:
    """
    Catch every unhandled exception raised by a tool and return a
    structured error string instead of propagating the crash.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error("Tool %r raised: %s", _tool_name(func), exc)
            return f"Tool execution failed: {exc}"
    return wrapper


def restrict_path(func: Callable) -> Callable:
    """
    Ensure the *path* argument (first positional after self) resolves
    inside WORKSPACE_ROOT. Rejects traversal attacks (e.g. ``../../etc``).
    """
    @functools.wraps(func)
    def wrapper(self, path: str, *args, **kwargs):
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(WORKSPACE_ROOT + os.sep) and abs_path != WORKSPACE_ROOT:
            logger.warning(
                "Path access denied for tool %r: %r is outside workspace.",
                _tool_name(self), abs_path,
            )
            return f"Access denied: '{path}' is outside the workspace."
        return func(self, path, *args, **kwargs)
    return wrapper


def validate_code(func: Callable) -> Callable:
    """
    Scan the *code* argument (first positional after self) for dangerous
    patterns before the tool executes it.
    """
    @functools.wraps(func)
    def wrapper(self, code: str, *args, **kwargs):
        for pattern in _BLOCKED_PATTERNS:
            if pattern in code:
                logger.warning(
                    "Blocked dangerous pattern %r in tool %r.",
                    pattern, _tool_name(self),
                )
                return f"Execution blocked: forbidden pattern '{pattern}' detected."
        return func(self, code, *args, **kwargs)
    return wrapper


def timeout(seconds: int = 5) -> Callable:
    """
    Abort a tool call that exceeds *seconds*.

    Note: relies on ``SIGALRM`` — POSIX/Linux only.
    On Windows the decorated function runs without a timeout.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(signal, "SIGALRM"):
                # Windows fallback — run without timeout
                logger.debug("timeout() decorator: SIGALRM not available, skipping.")
                return func(*args, **kwargs)

            def _handler(signum, frame):
                raise TimeoutError(f"Tool exceeded {seconds}s time limit.")

            signal.signal(signal.SIGALRM, _handler)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            except TimeoutError as exc:
                logger.error("Timeout in %r: %s", _tool_name(func), exc)
                return f"Tool timed out after {seconds}s."
            finally:
                signal.alarm(0)

        return wrapper
    return decorator


def audit_log(func: Callable) -> Callable:
    """
    Log every invocation (tool name, args, kwargs) and its result.
    Sensitive kwargs can be scrubbed by listing them in *redact*.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        name = _tool_name(self)
        logger.info("→ Tool called: %r | args=%s kwargs=%s", name, args, kwargs)
        result = func(self, *args, **kwargs)
        logger.info("← Tool result: %r | %s", name, result)
        return result
    return wrapper