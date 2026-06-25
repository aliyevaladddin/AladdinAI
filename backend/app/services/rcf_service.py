# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
import hmac
import hashlib
import time
from typing import Optional, Tuple

# [RCF:PROTECTED]
class RCFProtocol:
    """
    Restricted Correlation Framework (RCF) Protocol.
    Strictly controls the correlation between events through 
    cryptographic marker chaining and restricted execution flow.
    """
    
# [RCF:PROTECTED]
    @staticmethod
# [RCF:PROTECTED]
    def generate_marker(secret: str, last_marker: Optional[str], payload: str) -> Tuple[str, str]:
        """
        Generates a new RCF Marker and Chained Hash.
        The new marker depends on:
        1. The secret key
        2. The previous marker (The Chain)
        3. The current payload hash
        """
# [RCF:PROTECTED]
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        timestamp = str(int(time.time()))
        
        # Base string for the new marker
        # If no last_marker, we use the secret itself as the root
# [RCF:PROTECTED]
        chain_root = last_marker or hashlib.sha256(secret.encode()).hexdigest()
        
        base_str = f"{chain_root}:{payload_hash}:{timestamp}"
        
# [RCF:PROTECTED]
        new_marker = hmac.new(
            secret.encode(),
            base_str.encode(),
# [RCF:PROTECTED]
            hashlib.sha256
        ).hexdigest()
        
        return new_marker, timestamp

# [RCF:PROTECTED]
    @staticmethod
# [RCF:PROTECTED]
    def verify_chain(secret: str, last_marker: str, current_marker: str, payload: str, timestamp: str) -> bool:
        """
        Verifies if the current_marker is a valid successor of last_marker for the given payload.
        """
        expected_marker, _ = RCFProtocol.generate_marker(secret, last_marker, payload)
        # In a real RCF implementation, we would also check the timestamp window
# [RCF:PROTECTED]
        return hmac.compare_digest(expected_marker, current_marker)

# We'll need a way to store the 'last_marker' for each webhook to maintain the chain
