from __future__ import annotations

import os
import shutil
import subprocess

from app.core.exceptions import AppError

_OPENSSL_ENV_KEY = "SEC_ASSET_CREDENTIAL_ENCRYPTION_KEY"


class CredentialCipher:
    def __init__(
        self,
        *,
        encryption_key: str,
        openssl_binary: str = "openssl",
        iterations: int = 200_000,
    ) -> None:
        self.encryption_key = encryption_key.strip()
        self.openssl_binary = openssl_binary
        self.iterations = iterations

    def encrypt(self, plaintext: str) -> str:
        return self._run_openssl(
            decrypt=False,
            payload=plaintext.encode("utf-8"),
        ).decode("utf-8").strip()

    def decrypt(self, ciphertext: str) -> str:
        return self._run_openssl(
            decrypt=True,
            payload=ciphertext.encode("utf-8"),
        ).decode("utf-8")

    def _run_openssl(self, *, decrypt: bool, payload: bytes) -> bytes:
        if not self.encryption_key:
            raise AppError(
                message="Credential encryption key is not configured",
                status_code=500,
                code="credential_encryption_unavailable",
            )

        if shutil.which(self.openssl_binary) is None:
            raise AppError(
                message="OpenSSL is required for credential encryption",
                status_code=500,
                code="credential_encryption_unavailable",
            )

        command = [
            self.openssl_binary,
            "enc",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            str(self.iterations),
            "-salt",
            "-a",
            "-A",
            "-pass",
            f"env:{_OPENSSL_ENV_KEY}",
        ]
        if decrypt:
            command.append("-d")

        environment = os.environ.copy()
        environment[_OPENSSL_ENV_KEY] = self.encryption_key

        try:
            completed = subprocess.run(
                command,
                input=payload,
                capture_output=True,
                check=True,
                env=environment,
            )
        except subprocess.CalledProcessError as exc:
            raise AppError(
                message="Credential encryption operation failed",
                status_code=500,
                code="credential_encryption_failed",
            ) from exc

        return completed.stdout
