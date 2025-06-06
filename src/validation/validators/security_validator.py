"""
Security Validator

Validates security aspects of task execution and data handling.
"""

import re
import hashlib
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from urllib.parse import urlparse

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class SecurityValidator(BaseValidator):
    """Validates security aspects of task execution."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        
        # Security patterns and rules
        self.sensitive_patterns = {
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}-\d{3}-\d{4}\b',
            "api_key": r'\b[A-Za-z0-9]{32,}\b',
            "password": r'(?i)(password|pwd|pass)\s*[:=]\s*[^\s]+',
            "token": r'(?i)(token|auth|bearer)\s*[:=]\s*[^\s]+',
            "private_key": r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'
        }
        
        self.dangerous_domains = {
            'malware.com', 'phishing.org', 'suspicious.net'
        }
        
        self.allowed_protocols = {'http', 'https', 'ftp', 'ftps'}
        
        self.security_headers = {
            'content-security-policy',
            'x-frame-options',
            'x-content-type-options',
            'strict-transport-security',
            'x-xss-protection'
        }
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate security aspects."""
        if not self.config.security_checks:
            self.add_info("Security validation disabled", "config_check")
            return
        
        # Validate URLs and domains
        await self._validate_urls(context, evidence_collector)
        
        # Validate data privacy
        await self._validate_data_privacy(context, evidence_collector)
        
        # Validate input sanitization
        await self._validate_input_sanitization(context, evidence_collector)
        
        # Validate authentication and authorization
        await self._validate_auth(context, evidence_collector)
        
        # Validate network security
        await self._validate_network_security(context, evidence_collector)
        
        # Validate file operations
        await self._validate_file_operations(context, evidence_collector)
        
        # Validate compliance requirements
        if self.config.privacy_compliance:
            await self._validate_privacy_compliance(context, evidence_collector)
    
    async def _validate_urls(self, context: Dict[str, Any], 
                           evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate URLs for security issues."""
        urls = self._extract_urls(context)
        
        for url in urls:
            await self._validate_single_url(url, evidence_collector)
        
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "url_validation",
                {"validated_urls": urls, "timestamp": datetime.now(timezone.utc).isoformat()},
                "url_validation.json"
            )
    
    def _extract_urls(self, context: Dict[str, Any]) -> List[str]:
        """Extract URLs from context."""
        urls = []
        
        # From task definition
        task_definition = context.get("task_definition", {})
        if "url" in task_definition:
            urls.append(task_definition["url"])
        
        # From browser state
        browser_state = context.get("browser_state", {})
        if "url" in browser_state:
            urls.append(browser_state["url"])
        
        # From task result
        task_result = context.get("task_result", {})
        extracted_data = task_result.get("extracted_data", [])
        
        if isinstance(extracted_data, list):
            for item in extracted_data:
                if isinstance(item, str) and self._is_url(item):
                    urls.append(item)
                elif isinstance(item, dict):
                    for value in item.values():
                        if isinstance(value, str) and self._is_url(value):
                            urls.append(value)
        
        return list(set(urls))  # Remove duplicates
    
    def _is_url(self, text: str) -> bool:
        """Check if text is a URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def _validate_single_url(self, url: str, 
                                 evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate a single URL for security issues."""
        try:
            parsed_url = urlparse(url)
            
            # Validate protocol
            if parsed_url.scheme not in self.allowed_protocols:
                self.add_error(
                    f"Unsafe protocol in URL: {parsed_url.scheme}",
                    "unsafe_protocol",
                    {"url": url, "protocol": parsed_url.scheme},
                    f"Use only allowed protocols: {', '.join(self.allowed_protocols)}"
                )
            
            # Validate domain
            domain = parsed_url.netloc.lower()
            if domain in self.dangerous_domains:
                self.add_error(
                    f"Dangerous domain detected: {domain}",
                    "dangerous_domain",
                    {"url": url, "domain": domain},
                    "Avoid accessing known malicious domains"
                )
            
            # Check for suspicious patterns
            if self._has_suspicious_patterns(url):
                self.add_warning(
                    f"URL contains suspicious patterns: {url}",
                    "suspicious_url_pattern",
                    {"url": url},
                    "Review URL for potential security risks"
                )
            
            # Validate URL length
            if len(url) > 2048:
                self.add_warning(
                    f"Unusually long URL: {len(url)} characters",
                    "long_url",
                    {"url": url[:100] + "...", "length": len(url)},
                    "Long URLs may indicate malicious activity"
                )
            
        except Exception as e:
            self.add_error(
                f"Failed to validate URL: {str(e)}",
                "url_validation_error",
                {"url": url, "error": str(e)},
                "Check URL format and accessibility"
            )
    
    def _has_suspicious_patterns(self, url: str) -> bool:
        """Check for suspicious patterns in URL."""
        suspicious_patterns = [
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
            r'[a-zA-Z0-9]{20,}',  # Very long random strings
            r'%[0-9a-fA-F]{2}',  # URL encoding (could be obfuscation)
            r'javascript:',  # JavaScript URLs
            r'data:',  # Data URLs
        ]
        
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in suspicious_patterns)
    
    async def _validate_data_privacy(self, context: Dict[str, Any], 
                                   evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data privacy and sensitive information handling."""
        # Check extracted data for sensitive information
        task_result = context.get("task_result", {})
        extracted_data = task_result.get("extracted_data")
        
        if extracted_data:
            sensitive_findings = self._scan_for_sensitive_data(extracted_data)
            
            for finding in sensitive_findings:
                severity = ValidationSeverity.CRITICAL if finding["type"] in ["credit_card", "ssn", "private_key"] else ValidationSeverity.WARNING
                
                self.add_issue(
                    f"Sensitive data detected: {finding['type']}",
                    severity,
                    "sensitive_data_detected",
                    {
                        "data_type": finding["type"],
                        "location": finding["location"],
                        "pattern_matched": finding["pattern"][:20] + "..." if len(finding["pattern"]) > 20 else finding["pattern"]
                    },
                    "Implement data masking or secure handling for sensitive information"
                )
        
        # Collect privacy evidence
        if evidence_collector:
            privacy_summary = {
                "sensitive_data_found": len(sensitive_findings) if 'sensitive_findings' in locals() else 0,
                "data_types_detected": list(set(f["type"] for f in sensitive_findings)) if 'sensitive_findings' in locals() else [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.collect_evidence(
                evidence_collector,
                "privacy_validation",
                privacy_summary,
                "privacy_validation.json"
            )
    
    def _scan_for_sensitive_data(self, data: Any) -> List[Dict[str, Any]]:
        """Scan data for sensitive information patterns."""
        findings = []
        
        def scan_text(text: str, location: str) -> None:
            for data_type, pattern in self.sensitive_patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    findings.append({
                        "type": data_type,
                        "pattern": match.group(),
                        "location": location,
                        "start": match.start(),
                        "end": match.end()
                    })
        
        def scan_recursive(obj: Any, path: str = "root") -> None:
            if isinstance(obj, str):
                scan_text(obj, path)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    scan_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_recursive(item, f"{path}[{i}]")
        
        scan_recursive(data)
        return findings
    
    async def _validate_input_sanitization(self, context: Dict[str, Any], 
                                         evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate input sanitization and injection prevention."""
        task_definition = context.get("task_definition", {})
        user_inputs = self._extract_user_inputs(task_definition)
        
        for input_field, input_value in user_inputs.items():
            if self._has_injection_patterns(input_value):
                self.add_error(
                    f"Potential injection attack in input '{input_field}': {input_value[:50]}...",
                    "injection_attempt",
                    {"field": input_field, "value": input_value[:100]},
                    "Sanitize user inputs to prevent injection attacks"
                )
            
            if self._has_xss_patterns(input_value):
                self.add_error(
                    f"Potential XSS payload in input '{input_field}': {input_value[:50]}...",
                    "xss_attempt",
                    {"field": input_field, "value": input_value[:100]},
                    "Sanitize inputs to prevent XSS attacks"
                )
    
    def _extract_user_inputs(self, task_definition: Dict[str, Any]) -> Dict[str, str]:
        """Extract user inputs from task definition."""
        inputs = {}
        
        # Look for form data
        form_data = task_definition.get("form_data", {})
        if isinstance(form_data, dict):
            inputs.update(form_data)
        
        # Look for search queries
        search_query = task_definition.get("search_query")
        if search_query:
            inputs["search_query"] = search_query
        
        # Look for custom inputs
        custom_inputs = task_definition.get("inputs", {})
        if isinstance(custom_inputs, dict):
            inputs.update(custom_inputs)
        
        return inputs
    
    def _has_injection_patterns(self, text: str) -> bool:
        """Check for SQL injection patterns."""
        if not isinstance(text, str):
            return False
        
        injection_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(or|and)\s+\d+\s*=\s*\d+",
            r"(?i)'\s*(or|and)\s*'",
            r"(?i);.*--",
            r"(?i)/\*.*\*/",
        ]
        
        return any(re.search(pattern, text) for pattern in injection_patterns)
    
    def _has_xss_patterns(self, text: str) -> bool:
        """Check for XSS patterns."""
        if not isinstance(text, str):
            return False
        
        xss_patterns = [
            r"(?i)<script[^>]*>",
            r"(?i)javascript:",
            r"(?i)on\w+\s*=",
            r"(?i)<iframe[^>]*>",
            r"(?i)eval\s*\(",
            r"(?i)document\.(write|cookie)",
        ]
        
        return any(re.search(pattern, text) for pattern in xss_patterns)
    
    async def _validate_auth(self, context: Dict[str, Any], 
                           evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate authentication and authorization."""
        # Check for exposed credentials
        credentials = context.get("credentials", {})
        
        if credentials:
            # Check for weak passwords
            password = credentials.get("password", "")
            if password and self._is_weak_password(password):
                self.add_warning(
                    "Weak password detected",
                    "weak_password",
                    {"password_length": len(password)},
                    "Use strong passwords with mixed case, numbers, and symbols"
                )
            
            # Check for credentials in logs
            if self._credentials_in_logs(context):
                self.add_critical(
                    "Credentials found in logs",
                    "credentials_in_logs",
                    {},
                    "Remove credentials from log outputs immediately"
                )
    
    def _is_weak_password(self, password: str) -> bool:
        """Check if password is weak."""
        if len(password) < 8:
            return True
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return sum([has_upper, has_lower, has_digit, has_special]) < 3
    
    def _credentials_in_logs(self, context: Dict[str, Any]) -> bool:
        """Check if credentials appear in logs."""
        logs = context.get("execution_logs", [])
        credentials = context.get("credentials", {})
        
        if not logs or not credentials:
            return False
        
        for log_entry in logs:
            log_text = str(log_entry).lower()
            for cred_value in credentials.values():
                if isinstance(cred_value, str) and len(cred_value) > 3:
                    if cred_value.lower() in log_text:
                        return True
        
        return False
    
    async def _validate_network_security(self, context: Dict[str, Any], 
                                       evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate network security aspects."""
        # Check for HTTPS usage
        urls = self._extract_urls(context)
        
        for url in urls:
            parsed_url = urlparse(url)
            if parsed_url.scheme == "http" and parsed_url.netloc not in ["localhost", "127.0.0.1"]:
                self.add_warning(
                    f"Insecure HTTP connection: {url}",
                    "insecure_http",
                    {"url": url},
                    "Use HTTPS for secure communication"
                )
        
        # Check security headers
        response_headers = context.get("response_headers", {})
        if response_headers:
            missing_headers = self.security_headers - set(h.lower() for h in response_headers.keys())
            
            if missing_headers:
                self.add_warning(
                    f"Missing security headers: {', '.join(missing_headers)}",
                    "missing_security_headers",
                    {"missing_headers": list(missing_headers)},
                    "Implement security headers for better protection"
                )
    
    async def _validate_file_operations(self, context: Dict[str, Any], 
                                      evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate file operations for security."""
        file_operations = context.get("file_operations", [])
        
        for operation in file_operations:
            file_path = operation.get("path", "")
            operation_type = operation.get("type", "")
            
            # Check for path traversal
            if self._has_path_traversal(file_path):
                self.add_error(
                    f"Path traversal attempt detected: {file_path}",
                    "path_traversal",
                    {"path": file_path, "operation": operation_type},
                    "Sanitize file paths to prevent directory traversal"
                )
            
            # Check for dangerous file types
            if self._is_dangerous_file_type(file_path):
                self.add_warning(
                    f"Potentially dangerous file type: {file_path}",
                    "dangerous_file_type",
                    {"path": file_path, "operation": operation_type},
                    "Be cautious with executable and script files"
                )
    
    def _has_path_traversal(self, path: str) -> bool:
        """Check for path traversal patterns."""
        traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]
        
        return any(re.search(pattern, path, re.IGNORECASE) for pattern in traversal_patterns)
    
    def _is_dangerous_file_type(self, path: str) -> bool:
        """Check if file type is potentially dangerous."""
        dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.js', '.vbs', '.ps1', '.sh', '.php', '.asp'
        }
        
        return any(path.lower().endswith(ext) for ext in dangerous_extensions)
    
    async def _validate_privacy_compliance(self, context: Dict[str, Any], 
                                         evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate privacy compliance requirements."""
        # Check for data collection consent
        if not context.get("user_consent", False):
            self.add_warning(
                "No user consent recorded for data collection",
                "missing_consent",
                {},
                "Ensure proper consent is obtained before collecting personal data"
            )
        
        # Check for data retention policies
        if not context.get("data_retention_policy"):
            self.add_info(
                "No data retention policy specified",
                "missing_retention_policy",
                {},
                "Define data retention policies for compliance"
            )
        
        # Check for data anonymization
        extracted_data = context.get("task_result", {}).get("extracted_data")
        if extracted_data and self._contains_personal_data(extracted_data):
            if not context.get("data_anonymized", False):
                self.add_warning(
                    "Personal data collected without anonymization",
                    "personal_data_not_anonymized",
                    {},
                    "Consider anonymizing personal data for privacy protection"
                )
    
    def _contains_personal_data(self, data: Any) -> bool:
        """Check if data contains personal information."""
        personal_data_patterns = [
            "email", "phone", "address", "name", "ssn", "credit_card"
        ]
        
        sensitive_findings = self._scan_for_sensitive_data(data)
        return any(finding["type"] in personal_data_patterns for finding in sensitive_findings)
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security validation summary."""
        return {
            "sensitive_patterns": list(self.sensitive_patterns.keys()),
            "dangerous_domains": list(self.dangerous_domains),
            "allowed_protocols": list(self.allowed_protocols),
            "security_headers": list(self.security_headers),
            "validation_rules": self.get_validation_rules()
        }
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "unsafe_protocol",
            "dangerous_domain",
            "suspicious_url_pattern",
            "long_url",
            "url_validation_error",
            "sensitive_data_detected",
            "injection_attempt",
            "xss_attempt",
            "weak_password",
            "credentials_in_logs",
            "insecure_http",
            "missing_security_headers",
            "path_traversal",
            "dangerous_file_type",
            "missing_consent",
            "missing_retention_policy",
            "personal_data_not_anonymized"
        ]
