# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import platform
import subprocess
from typing import TYPE_CHECKING

from .Logger import consoleLogger

if TYPE_CHECKING:
    pass

__all__ = [
    "AESEncryptor",
    "RSAEncryptor",
]

_DEFAULT_LOGGER = consoleLogger("Security")

# Define the AES and RSA encryptor classes
try:
    import keyring
    # noinspection PyPackageRequirements
    from Crypto.Cipher import AES, PKCS1_OAEP
    # noinspection PyPackageRequirements
    from Crypto.Random import get_random_bytes
    # noinspection PyPackageRequirements
    from Crypto.Util.Padding import unpad
    # noinspection PyPackageRequirements
    from Crypto.PublicKey import RSA


    class _BaseEncryptor:
        def __init__(self, name: str, identifier: str):
            self._Name = name
            self._Key = self._generateIdentifier() if identifier is None else identifier
            self._AESKey = self._loadAESKey()

        def _generateIdentifier(self) -> str:
            try:
                os_type = platform.system()
                if os_type == "Windows":
                    serial_number = subprocess.check_output("wmic baseboard get SerialNumber", shell=True).decode().split('\n')[1].strip()
                    key_name = str(serial_number)
                    _DEFAULT_LOGGER.debug(f"[Windows] Serial number : {key_name}")
                elif os_type == "Darwin":
                    info = subprocess.check_output(["system_profiler", "SPHardwareDataType"]).decode()
                    lines = info.split('\n')
                    serial_line = next((line for line in lines if "Serial Number (system)" in line), None)
                    serial_number = serial_line.split(':')[1].strip() if serial_line else "UnknownSerial"
                    key_name = str(serial_number)
                    _DEFAULT_LOGGER.debug(f"[Darwin] Serial number : {key_name}")
                else:
                    _DEFAULT_LOGGER.error(f"Generate identifier error : Unsupported OS type.", exc_info=True)
                    return f"{self._Name}"
                return key_name
            except Exception as e:
                _DEFAULT_LOGGER.error(f"Generate identifier error : {e}", exc_info=True)
                return f"{self._Name}"

        def _loadAESKey(self) -> bytes | None:
            try:
                encoded_key = keyring.get_password(self._Key, self._Name)
                if encoded_key:
                    return base64.b64decode(encoded_key)
                else:
                    aes_key = get_random_bytes(32)
                    self._saveAESKey(aes_key)
                    return aes_key
            except Exception as e:
                _DEFAULT_LOGGER.error(f"Load AES key error : {e}", exc_info=True)

        def _saveAESKey(self, key):
            try:
                encoded_key = base64.b64encode(key).decode("utf-8")
                keyring.set_password(self._Key, self._Name, encoded_key)
            except Exception as e:
                _DEFAULT_LOGGER.error(f"Save AES key error : {e}", exc_info=True)


    class AESEncryptor(_BaseEncryptor):
        def __init__(self, name: str, identifier: str = None):
            super().__init__(name, identifier)

        def encrypt(self, data: str) -> str:
            try:
                iv = get_random_bytes(12)
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                encrypted_data, tag = aes_cipher.encrypt_and_digest(str(data).encode())
                combined_data = iv + tag + encrypted_data
                return base64.b64encode(combined_data).decode()
            except Exception as e:
                _DEFAULT_LOGGER.error(f"AES encrypt data error : {e}", exc_info=True)
                return ""

        def decrypt(self, data: str) -> str:
            try:
                combined_data = base64.b64decode(data)
                iv = combined_data[:12]
                tag = combined_data[12:28]
                encrypted_data = combined_data[28:]
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                decrypted_data = aes_cipher.decrypt_and_verify(encrypted_data, tag).decode()
                return decrypted_data
            except Exception as e:
                _DEFAULT_LOGGER.error(f"AES decrypt data error : {e}", exc_info=True)
                return ""


    class RSAEncryptor(_BaseEncryptor):
        def __init__(self, name: str, identifier: str = None):
            super().__init__(name, identifier)

        @staticmethod
        def generateRSAKeys(private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple[bytes, bytes] | None:
            if key_size not in [1024, 2048, 3072, 4096]:
                _DEFAULT_LOGGER.warning(f"Invalid rsa key size: {key_size}. Using default size 2048.")
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                _DEFAULT_LOGGER.error("RSA keys storage paths not provided.", exc_info=True)
                return None

            key = RSA.generate(key_size)
            private_key = key.export_key()
            public_key = key.publickey().export_key()

            if store_locally:
                with open(public_path, 'wb') as pub_file:
                    pub_file.write(public_key)
                with open(private_path, 'wb') as priv_file:
                    priv_file.write(public_key)
            return private_key, public_key

        @staticmethod
        def loadRSAPrivateKey(private_path: str) -> RSA.RsaKey:
            try:
                with open(private_path, 'rb') as priv_file:
                    private_key = priv_file.read()
                return RSA.import_key(private_key)
            except Exception as e:
                _DEFAULT_LOGGER.error(f"Load rsa private key error : {e}", exc_info=True)
                return None

        @staticmethod
        def loadRSAPublicKey(public_path: str) -> RSA.RsaKey:
            try:
                with open(public_path, 'rb') as pub_file:
                    public_key = pub_file.read()
                return RSA.import_key(public_key)
            except Exception as e:
                _DEFAULT_LOGGER.error(f"Load rsa public key error : {e}", exc_info=True)
                return None

        @staticmethod
        def rsaEncrypt(public_key: bytes, data: str) -> bytes:
            public_key_obj = RSA.import_key(public_key)
            cipher_rsa = PKCS1_OAEP.new(public_key_obj)
            encrypted_data = cipher_rsa.encrypt(data.encode())
            return encrypted_data

        @staticmethod
        def rsaDecrypt(private_key: bytes, encrypted_data: bytes) -> str:
            private_key_obj = RSA.import_key(private_key)
            cipher_rsa = PKCS1_OAEP.new(private_key_obj)
            decrypted_data = cipher_rsa.decrypt(encrypted_data)
            return decrypted_data.decode()
except ImportError as _:
    class AESEncryptor:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("AESEncryptor is not available. Please install keyring, pycryptodome packages.")

        def encrypt(self, data: str) -> str:
            raise NotImplementedError("AESEncryptor is not available. Please install keyring, pycryptodome packages.")

        def decrypt(self, data: str) -> str:
            raise NotImplementedError("AESEncryptor is not available. Please install keyring, pycryptodome packages.")


    class RSAEncryptor:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

        @staticmethod
        def generateRSAKeys(private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple[bytes, bytes] | None:
            raise NotImplementedError("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

        @staticmethod
        def loadRSAPrivateKey(private_path: str) -> RSA.RsaKey:
            raise NotImplementedError("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

        @staticmethod
        def loadRSAPublicKey(public_path: str) -> RSA.RsaKey:
            raise NotImplementedError("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

        @staticmethod
        def rsaEncrypt(public_key: bytes, data: str) -> bytes:
            raise NotImplementedError("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

        @staticmethod
        def rsaDecrypt(private_key: bytes, encrypted_data: bytes) -> str:
            raise NotImplementedError("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")
