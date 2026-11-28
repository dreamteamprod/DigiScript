"""Password service for hashing, verification, and generation"""

import secrets

import bcrypt
import xkcdpass.xkcd_password as xp
from tornado import escape
from tornado.ioloop import IOLoop


class PasswordService:
    """Service for password-related operations"""

    #: Minimum accepted password length, in characters.
    MIN_PASSWORD_LENGTH = 8

    #: Lazily generated bcrypt hash of a random throwaway string. Verified
    #: against when a login names an unknown user so the response time matches
    #: a real user. Generated at runtime so no hash literal lives in the source.
    _dummy_hash: str | None = None

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
    async def verify_dummy_password(password: str) -> None:
        """
        Spend the same time as a real verification, against a fixed dummy hash.

        Used when the username does not exist so response timing does not reveal
        which usernames are registered. The result is always discarded.

        :param password: Plain text password submitted by the client
        :type password: str
        """
        if PasswordService._dummy_hash is None:
            # Generating the hash costs one bcrypt run, the same as a
            # verification, so the first call is no slower than later ones.
            # Concurrent first calls may each generate one; the extra results
            # are simply overwritten.
            PasswordService._dummy_hash = await PasswordService.hash_password(
                secrets.token_urlsafe(16)
            )
            return
        await PasswordService.verify_password(password, PasswordService._dummy_hash)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validate password meets strength requirements.

        Current requirements:
        - Minimum 8 characters
        - Maximum 72 bytes when UTF-8 encoded (bcrypt hard limit)

        :param password: Password to validate
        :type password: str
        :return: Tuple of (is_valid, error_message). is_valid is True if password
                 meets requirements. error_message is empty string if valid, error
                 description if invalid.
        :rtype: tuple[bool, str]
        """
        if len(password) < PasswordService.MIN_PASSWORD_LENGTH:
            return False, (
                f"Password must be at least {PasswordService.MIN_PASSWORD_LENGTH} "
                "characters long"
            )

        if len(password.encode("utf-8")) > 72:
            return False, "Password must be 72 characters or fewer"

        return True, ""

    @staticmethod
    def generate_temporary_password(word_count: int = 4) -> str:
        """
        Generate a human-readable temporary password using EFF wordlist.

        Uses the xkcdpass library with the EFF long wordlist (7776 words)
        for cryptographically secure passphrase generation.

        - 3 words = ~38.7 bits of entropy
        - 4 words = ~51.6 bits of entropy

        :param word_count: Number of words to use (default: 4)
        :type word_count: int
        :return: Dash-separated password like "correct-horse-battery-staple"
        :rtype: str
        """
        wordlist = xp.generate_wordlist(wordfile=xp.locate_wordfile())
        # Exclude words containing hyphens to keep the dash-delimiter unambiguous
        wordlist = [w for w in wordlist if "-" not in w]
        password = xp.generate_xkcdpassword(
            wordlist, numwords=word_count, delimiter="-"
        )
        return password
