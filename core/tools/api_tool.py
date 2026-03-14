"""
HTTP/API tool for making safe API requests.
Includes input validation, timeout protection, and error handling.
"""
from typing import Any, Dict, Optional
import json
from urllib.parse import urlparse

from .base import BaseTool
from .code_security_decorator import safe_execution, timeout, audit_log

try:
    import requests
except ImportError:
    requests = None


# Whitelist of allowed domains for API calls
ALLOWED_DOMAINS = {
    "api.example.com",
    "api.openai.com",
    "api.anthropic.com",
    "api.github.com",
    # Add more trusted domains as needed
}

# Block dangerous patterns in URLs
BLOCKED_URL_PATTERNS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "192.168.",
    "10.0.",
    "172.16.",
    "file://",
]


class HTTPRequestTool(BaseTool):
    """
    Makes secure HTTP requests to external APIs.
    Includes URL validation, timeout protection, and response size limits.
    """
    name = "http_request"
    description = (
        "Makes an HTTP request to an API. "
        "Provide 'url', 'method' (GET/POST), 'headers' (optional), "
        "and 'data' (optional) arguments."
    )
    
    @safe_execution
    @timeout(seconds=30)
    @audit_log
    def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """Execute an HTTP request with security validations."""
        
        if not requests:
            return "Error: requests library not installed."
        
        # Validate URL
        validation_error = self._validate_url(url)
        if validation_error:
            return f"Error: {validation_error}"
        
        # Validate method
        method = method.upper()
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]:
            return f"Error: Invalid HTTP method '{method}'. Allowed: GET, POST, PUT, DELETE, PATCH, HEAD"
        
        # Sanitize headers
        if headers is None:
            headers = {}
        headers = self._sanitize_headers(headers)
        
        # Limit request size
        if data:
            data_str = json.dumps(data) if isinstance(data, dict) else str(data)
            if len(data_str) > 10000:
                return "Error: Request data too large (max 10KB)."
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if isinstance(data, dict) else None,
                timeout=10,
                verify=True,
            )
            
            # Limit response size
            if len(response.content) > 1000000:  # 1MB limit
                return "Error: Response too large (max 1MB)."
            
            # Try to parse as JSON, fall back to text
            try:
                result = response.json()
            except:
                result = response.text
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": result,
            }
            
        except requests.Timeout:
            return "Error: Request timeout (exceeded 10 seconds)."
        except requests.ConnectionError as e:
            return f"Error: Connection failed: {str(e)}"
        except Exception as e:
            return f"Error: Request failed: {str(e)}"
    
    def _validate_url(self, url: str) -> Optional[str]:
        """Validate URL for security concerns."""
        if not isinstance(url, str):
            return "'url' must be a string"
        
        if len(url) > 2048:
            return "URL too long (max 2048 characters)"
        
        # Check for dangerous patterns
        for pattern in BLOCKED_URL_PATTERNS:
            if pattern in url.lower():
                return f"URL contains blocked pattern: '{pattern}'"
        
        # Parse and validate URL structure
        try:
            parsed = urlparse(url)
        except Exception:
            return "Invalid URL format"
        
        if not parsed.scheme or parsed.scheme not in ["http", "https"]:
            return "Only HTTP and HTTPS protocols are allowed"
        
        if not parsed.netloc:
            return "URL must have a valid domain"
        
        # Optional: Check against whitelist
        # Uncomment if you want to enforce strict domain whitelist
        # domain = parsed.netloc.lower()
        # if domain not in ALLOWED_DOMAINS:
        #     return f"Domain '{domain}' not in whitelist. Allowed: {ALLOWED_DOMAINS}"
        
        return None
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove potentially dangerous headers."""
        # Whitelist of safe headers
        safe_header_prefixes = ["content-", "accept", "authorization", "x-"]
        blocked_headers = {"host", "content-length", "transfer-encoding"}
        
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            
            # Block dangerous headers
            if key_lower in blocked_headers:
                continue
            
            # Allow common safe headers
            is_safe = any(
                key_lower.startswith(prefix) for prefix in safe_header_prefixes
            )
            
            if is_safe and isinstance(value, str):
                sanitized[key] = value
        
        return sanitized


class APIClientTool(BaseTool):
    """
    High-level API client for making structured API calls.
    Simplifies JSON API usage with preset configurations.
    """
    name = "api_client"
    description = (
        "Makes a structured JSON API request. "
        "Provide 'endpoint', 'method', and optional 'params' and 'body'."
    )
    
    # Base URLs for different API services (can be configured)
    API_BASES = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "github": "https://api.github.com",
    }
    
    @safe_execution
    @timeout(seconds=30)
    @audit_log
    def execute(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Execute a structured API request."""
        
        if not requests:
            return "Error: requests library not installed."
        
        if not endpoint or not isinstance(endpoint, str):
            return "Error: 'endpoint' must be a non-empty string"
        
        method = method.upper()
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return "Error: Invalid method"
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            response = requests.request(
                method=method,
                url=endpoint,
                headers=headers,
                params=params,
                json=body,
                timeout=10,
                verify=True,
            )
            
            return {
                "status": response.status_code,
                "data": response.json() if response.text else None,
            }
            
        except Exception as e:
            return f"Error: API request failed: {str(e)}"
