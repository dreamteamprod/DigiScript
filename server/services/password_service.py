"""Password service for hashing, verification, and generation"""

import bcrypt
import xkcdpass.xkcd_password as xp
from tornado import escape
from tornado.ioloop import IOLoop


class PasswordService:
    """Service for password-related operations"""

    @staticmethod
    async def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with auto-generated salt.

        :param password: Plain text password to hash
        :type password: str
        :return: Bcrypt hash string suitable for database storage
        :rtype: str
        """
        loop = IOLoop.current()
        hashed = await loop.run_in_executor(
            None, bcrypt.hashpw, escape.utf8(password), bcrypt.gensalt()
        )
        return escape.to_unicode(hashed)

    @staticmethod
    async def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a bcrypt hash.

        :param password: Plain text password to verify
        :type password: str
        :param hashed: Bcrypt hash to verify against
        :type hashed: str
        :return: True if password matches hash, False otherwise
        :rtype: bool
        """
        loop = IOLoop.current()
        matches = await loop.run_in_executor(
            None, bcrypt.checkpw, escape.utf8(password), escape.utf8(hashed)
        )
        return matches

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validate password meets strength requirements.

        Current requirements:
        - Minimum 6 characters

        :param password: Password to validate
        :type password: str
        :return: Tuple of (is_valid, error_message). is_valid is True if password
                 meets requirements. error_message is empty string if valid, error
                 description if invalid.
        :rtype: tuple[bool, str]
        """
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"

        return True, ""

    @staticmethod
    def generate_temporary_password(word_count: int = 3) -> str:
        """
        Generate a human-readable temporary password using EFF wordlist.

        Uses the xkcdpass library with the EFF long wordlist (7776 words)
        for cryptographically secure passphrase generation.

        - 3 words = ~38.7 bits of entropy
        - 4 words = ~51.6 bits of entropy

        :param word_count: Number of words to use (default: 3)
        :type word_count: int
        :return: Dash-separated password like "correct-horse-battery"
        :rtype: str
        """
        wordlist = xp.generate_wordlist(wordfile=xp.locate_wordfile())
        password = xp.generate_xkcdpassword(
            wordlist, numwords=word_count, delimiter="-"
        )
        return password
