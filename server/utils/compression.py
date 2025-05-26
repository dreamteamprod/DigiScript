import base64
import json
import zlib
from typing import Dict, List, Union, Any


def compress_script_data(script_data: Union[Dict, List]) -> str:
    """
    Compresses script data using zlib and encodes it as base64 for storage.
    
    Args:
        script_data: Dictionary or list containing script data to compress
        
    Returns:
        Base64 encoded compressed data string
    """
    json_data = json.dumps(script_data)
    
    compressed_data = zlib.compress(json_data.encode('utf-8'))
    
    base64_data = base64.b64encode(compressed_data).decode('ascii')
    
    return base64_data


def decompress_script_data(compressed_data: str) -> Union[Dict, List, Any]:
    """
    Decompresses script data from base64 encoded zlib compressed format.
    
    Args:
        compressed_data: Base64 encoded compressed data string
        
    Returns:
        Original script data as dictionary or list
    """
    if not compressed_data:
        return None
        
    binary_data = base64.b64decode(compressed_data)
    
    decompressed_data = zlib.decompress(binary_data)
    
    script_data = json.loads(decompressed_data.decode('utf-8'))
    
    return script_data
