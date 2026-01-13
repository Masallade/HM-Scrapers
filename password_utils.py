"""
Password Utility
Simple utility to get passwords from database (plain text only)
"""


def get_password(password):
    """
    Get password from database (plain text)
    
    Args:
        password (str|None): Plain text password from database
        
    Returns:
        str|None: Password or None if invalid
    """
    if not password:
        return None
    
    # Return password as-is (plain text)
    return password



