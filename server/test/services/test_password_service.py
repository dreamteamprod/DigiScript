from tornado.testing import AsyncTestCase, gen_test

from services.password_service import PasswordService


class TestPasswordService(AsyncTestCase):
    """Unit tests for PasswordService"""

    @gen_test
    async def test_hash_password_returns_valid_bcrypt_hash(self):
        """Test that hash_password returns a valid bcrypt hash string"""
        password = "test_password_123"
        hashed = await PasswordService.hash_password(password)

        # Bcrypt hashes are always 60 characters and start with $2b$ or $2a$
        self.assertIsNotNone(hashed)
        self.assertEqual(60, len(hashed))
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))

    @gen_test
    async def test_hash_password_produces_different_hashes(self):
        """Test that hashing the same password twice produces different hashes"""
        password = "test_password_123"
        hash1 = await PasswordService.hash_password(password)
        hash2 = await PasswordService.hash_password(password)

        # Each hash should be unique due to random salt
        self.assertNotEqual(hash1, hash2)

    @gen_test
    async def test_verify_password_with_correct_password(self):
        """Test that verify_password returns True for correct password"""
        password = "correct_password"
        hashed = await PasswordService.hash_password(password)

        result = await PasswordService.verify_password(password, hashed)
        self.assertTrue(result)

    @gen_test
    async def test_verify_password_with_incorrect_password(self):
        """Test that verify_password returns False for incorrect password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = await PasswordService.hash_password(password)

        result = await PasswordService.verify_password(wrong_password, hashed)
        self.assertFalse(result)

    @gen_test
    async def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        password = "TestPassword123"
        hashed = await PasswordService.hash_password(password)

        result = await PasswordService.verify_password("testpassword123", hashed)
        self.assertFalse(result)

    def test_validate_password_strength_minimum_length(self):
        """Test that passwords must be at least 6 characters"""
        # Valid passwords
        is_valid, error_msg = PasswordService.validate_password_strength("123456")
        self.assertTrue(is_valid)
        self.assertEqual("", error_msg)

        is_valid, error_msg = PasswordService.validate_password_strength(
            "longer_password"
        )
        self.assertTrue(is_valid)
        self.assertEqual("", error_msg)

    def test_validate_password_strength_too_short(self):
        """Test that passwords under 6 characters are rejected"""
        is_valid, error_msg = PasswordService.validate_password_strength("12345")
        self.assertFalse(is_valid)
        self.assertEqual("Password must be at least 6 characters long", error_msg)

        is_valid, error_msg = PasswordService.validate_password_strength("")
        self.assertFalse(is_valid)
        self.assertEqual("Password must be at least 6 characters long", error_msg)

    def test_generate_temporary_password_default_word_count(self):
        """Test that generate_temporary_password produces 3-word password by default"""
        password = PasswordService.generate_temporary_password()

        # Should be dash-separated words
        words = password.split("-")
        self.assertEqual(3, len(words))

        # Each word should be non-empty and alphanumeric
        for word in words:
            self.assertGreater(len(word), 0)
            self.assertTrue(word.isalpha())

    def test_generate_temporary_password_custom_word_count(self):
        """Test that generate_temporary_password respects word_count parameter"""
        for word_count in [2, 3, 4, 5]:
            password = PasswordService.generate_temporary_password(
                word_count=word_count
            )
            words = password.split("-")
            self.assertEqual(word_count, len(words))

    def test_generate_temporary_password_uniqueness(self):
        """Test that generate_temporary_password produces unique passwords"""
        passwords = set()
        for _ in range(10):
            password = PasswordService.generate_temporary_password()
            passwords.add(password)

        # With 7776 words in EFF wordlist, collision probability is extremely low
        # All 10 passwords should be unique
        self.assertEqual(10, len(passwords))

    def test_generate_temporary_password_format(self):
        """Test that generated passwords only contain lowercase letters and dashes"""
        password = PasswordService.generate_temporary_password()

        # Should only contain lowercase letters and dashes
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz-")
        self.assertTrue(all(c in allowed_chars for c in password))

        # Should not start or end with dash
        self.assertFalse(password.startswith("-"))
        self.assertFalse(password.endswith("-"))

    def test_generate_temporary_password_meets_minimum_length(self):
        """Test that generated temporary passwords meet 6-character minimum"""
        password = PasswordService.generate_temporary_password()
        is_valid, _ = PasswordService.validate_password_strength(password)

        # Generated passwords should always be valid
        self.assertTrue(is_valid)
        self.assertGreaterEqual(len(password), 6)
