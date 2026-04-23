"""
Log Preprocessing: Tokenization, Normalization, PII Masking
"""
import re
import hashlib
from typing import Dict, Any, List
from datetime import datetime

class LogPreprocessor:
    def __init__(self, mask_pii: bool = True):
        self.mask_pii = mask_pii
        
        # Patterns for PII detection
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'api_key': r'[A-Za-z0-9]{32,}',
            'jwt_token': r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'
        }
        
        # Common log patterns for normalization
        self.normalization_patterns = {
            'timestamp': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            'uuid': r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'number': r'\b\d+\b',
            'path': r'/[a-zA-Z0-9/._-]+',
        }
        
    def mask_pii_data(self, text: str) -> str:
        """Mask PII data in log messages"""
        if not self.mask_pii:
            return text
            
        masked_text = text
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, masked_text)
            for match in matches:
                # Replace with hash of the value for consistency
                hash_value = hashlib.md5(match.encode()).hexdigest()[:8]
                masked_text = masked_text.replace(match, f"[{pii_type.upper()}_{hash_value}]")
                
        return masked_text
    
    def normalize_log(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize log entry structure"""
        normalized = {}
        
        # Standardize timestamp
        if 'timestamp' in log_entry:
            try:
                dt = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                normalized['timestamp'] = dt.isoformat()
            except:
                normalized['timestamp'] = datetime.utcnow().isoformat()
        
        # Standardize log level
        if 'level' in log_entry:
            level = log_entry['level'].upper()
            normalized['level'] = level
            # Map to severity score
            severity_map = {
                'DEBUG': 0.1,
                'INFO': 0.2,
                'WARNING': 0.5,
                'ERROR': 0.8,
                'CRITICAL': 1.0
            }
            normalized['severity_score'] = severity_map.get(level, 0.5)
        
        # Mask PII in message
        if 'message' in log_entry:
            normalized['message'] = self.mask_pii_data(log_entry['message'])
            # Add tokenized version
            normalized['tokens'] = self.tokenize(log_entry['message'])
        
        # Preserve source
        if 'source' in log_entry:
            normalized['source'] = log_entry['source']
        
        # Process metadata
        if 'metadata' in log_entry:
            normalized['metadata'] = {}
            for key, value in log_entry['metadata'].items():
                if isinstance(value, str):
                    normalized['metadata'][key] = self.mask_pii_data(value)
                else:
                    normalized['metadata'][key] = value
        
        return normalized
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize log message into tokens"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-_\.:]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Remove short tokens (less than 2 characters)
        tokens = [t for t in tokens if len(t) > 2]
        
        # Remove common stop words (log-specific)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        tokens = [t for t in tokens if t not in stop_words]
        
        return tokens
    
    def extract_entities(self, log_entry: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract entities from log entry using regex patterns"""
        entities = {
            'ips': [],
            'emails': [],
            'paths': [],
            'numbers': [],
            'error_codes': []
        }
        
        message = log_entry.get('message', '')
        
        # Extract IP addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        entities['ips'] = re.findall(ip_pattern, message)
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, message)
        
        # Extract file paths
        path_pattern = r'/[a-zA-Z0-9/._-]+'
        entities['paths'] = re.findall(path_pattern, message)
        
        # Extract numbers
        num_pattern = r'\b\d+\b'
        entities['numbers'] = re.findall(num_pattern, message)
        
        # Extract error codes (like ERR_123, E1234)
        error_pattern = r'\b(?:ERR|E|ERROR)[_-]?\d+\b'
        entities['error_codes'] = re.findall(error_pattern, message, re.IGNORECASE)
        
        return entities
    
    def preprocess(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Complete preprocessing pipeline"""
        # Normalize the log
        processed = self.normalize_log(log_entry)
        
        # Extract entities
        processed['entities'] = self.extract_entities(log_entry)
        
        # Add processing metadata
        processed['processed_at'] = datetime.utcnow().isoformat()
        processed['has_pii'] = any(
            re.search(pattern, log_entry.get('message', '')) 
            for pattern in self.pii_patterns.values()
        )
        
        return processed

# Test the preprocessor
if __name__ == "__main__":
    preprocessor = LogPreprocessor()
    
    sample_log = {
        "timestamp": "2024-04-02T10:30:00Z",
        "level": "ERROR",
        "source": "api",
        "message": "User john.doe@example.com from IP 192.168.1.100 failed to authenticate. API key: abc123xyz456",
        "metadata": {
            "user_id": "john.doe@example.com",
            "trace_id": "trace_123"
        }
    }
    
    processed = preprocessor.preprocess(sample_log)
    print("Original:", sample_log['message'])
    print("Processed:", processed['message'])
    print("Tokens:", processed['tokens'])
    print("Entities:", processed['entities'])
    print("Has PII:", processed['has_pii'])
