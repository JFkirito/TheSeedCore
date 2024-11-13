# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "AESEncryptor",
    "RSAEncryptor"
]

import base64
import platform
import subprocess
from typing import TYPE_CHECKING

from .Logger import consoleLogger

if TYPE_CHECKING:
    pass

_DefaultLogger = consoleLogger("Security")

# Define the AES and RSA encryptor classes
try:
    import keyring
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import unpad
    from Crypto.PublicKey import RSA


    class _BaseEncryptor:
        """
        _BaseEncryptor class serves as a base class for encryption utilities, handling the generation and management of encryption keys.

        The class serves as a foundational class for encryption utilities, providing methods for generating and managing encryption keys.
        This class supports both the secure generation of unique identifiers and the storage, loading, and management of AES keys,
        making it a reliable base for specialized encryption classes.

        ClassAttributes:
            name: The name of the encryptor instance.
            identifier: A unique identifier for the encryptor instance.
            _Key: The generated or provided key used for accessing the encryption key storage.
            _AESKey: The AES encryption key loaded from the key storage or generated if not available.

        Methods:
            _generateIdentifier: Generates a unique identifier based on the system's serial number, depending on the operating system.
            _loadAESKey: Loads the AES key from a secure storage; generates and saves a new key if not found.
            _saveAESKey: Saves the provided AES key to a secure storage after encoding it.
        """

        def __init__(self, name: str, identifier: str):
            self._Name = name
            self._Key = self._generateIdentifier() if identifier is None else identifier
            self._AESKey = self._loadAESKey()

        def _generateIdentifier(self) -> str:
            """
            Generates a unique identifier based on the system's serial number.

            This method checks the operating system type and retrieves the serial number from the system's hardware information.
            If the OS is Windows, it uses the WMIC command; for macOS (Darwin), it uses system_profiler to obtain the serial number.
            In case of an unsupported OS or any error during the retrieval process, it logs the error and returns the name of the instance.

            :return: A string representing the unique identifier, which is the serial number of the hardware, or the instance name if an error occurs.

            :raise: Raises an exception if there is an error in fetching the serial number and logs the error details.

            setup:
                1. Determine the operating system type using platform.system().
                2. For Windows, execute a WMIC command to get the serial number.
                3. For macOS, use system_profiler to fetch hardware details and extract the serial number.
                4. If an unsupported OS is detected or if an error occurs, log the error and return the instance name.
            """

            try:
                os_type = platform.system()
                if os_type == "Windows":
                    serial_number = subprocess.check_output("wmic baseboard get SerialNumber", shell=True).decode().split('\n')[1].strip()
                    key_name = str(serial_number)
                    _DefaultLogger.debug(f"[Windows] Serial number : {key_name}")
                elif os_type == "Darwin":
                    info = subprocess.check_output(["system_profiler", "SPHardwareDataType"]).decode()
                    lines = info.split('\n')
                    serial_line = next((line for line in lines if "Serial Number (system)" in line), None)
                    serial_number = serial_line.split(':')[1].strip() if serial_line else "UnknownSerial"
                    key_name = str(serial_number)
                    _DefaultLogger.debug(f"[Darwin] Serial number : {key_name}")
                else:
                    _DefaultLogger.error(f"Generate identifier error : Unsupported OS type.", exc_info=True)
                    return f"{self._Name}"
                return key_name
            except Exception as e:
                _DefaultLogger.error(f"Generate identifier error : {e}", exc_info=True)
                return f"{self._Name}"

        def _loadAESKey(self) -> bytes | None:
            """
            Loads the AES key from secure storage using keyring.

            This method retrieves the AES key from the keyring. If the key does not exist, a new random AES key is generated, saved, and returned.

            :return: The AES key as a bytes object if successful; returns None if the key cannot be retrieved and logs an error.

            :raise: Raises an exception if there is an error during the retrieval or decoding process, logging the error details.

            setup:
                1. Attempt to retrieve the encoded AES key from the keyring.
                2. If the key is found, decode it from base64.
                3. If the key is not found, generate a new random AES key, save it, and return the new key.
            """

            try:
                encoded_key = keyring.get_password(self._Key, self._Name)
                if encoded_key:
                    return base64.b64decode(encoded_key)
                else:
                    aes_key = get_random_bytes(32)
                    self._saveAESKey(aes_key)
                    return aes_key
            except Exception as e:
                _DefaultLogger.error(f"Load AES key error : {e}", exc_info=True)

        def _saveAESKey(self, key):
            """
            Saves the AES key to a secure storage using keyring.

            This method encodes the provided AES key in base64 and stores it using the keyring library, which provides a secure way to manage sensitive information.

            :param key: The AES key to be saved, expected to be a bytes object.

            :return: None. Logs an error if saving the key fails.
            :raise: Raises an exception if there is an error during the encoding or saving process, logging the error details.

            setup:
                1. Encode the AES key in base64 format.
                2. Store the encoded key using keyring with the specified key and name.
            """

            try:
                encoded_key = base64.b64encode(key).decode("utf-8")
                keyring.set_password(self._Key, self._Name, encoded_key)
            except Exception as e:
                _DefaultLogger.error(f"Save AES key error : {e}", exc_info=True)


    class AESEncryptor(_BaseEncryptor):
        """
        AESEncryptor class for handling AES encryption and decryption operations.

        The class provides a secure interface for performing AES encryption and decryption operations.
        It uses the AES algorithm in GCM (Galois/Counter Mode) for encryption, which offers both confidentiality and data integrity.

        ClassAttributes:
            name: The name of the AESEncryptor instance.
            identifier: An optional identifier for the AESEncryptor instance.
            _AESKey: The key used for AES encryption and decryption.

        Methods:
            encrypt: Encrypts the provided data using AES encryption in GCM mode.
            decrypt: Decrypts the provided encrypted data back to its original form.
        """

        def __init__(self, name: str, identifier: str = None):
            super().__init__(name, identifier)

        def encrypt(self, data: str) -> str:
            """
            Encrypts the provided data using AES encryption.

            This method generates a random initialization vector (IV), uses AES in GCM mode to encrypt the data, and then combines the IV, authentication tag, and encrypted data. The result is returned as a base64 encoded string.

            :param data: The plaintext string that needs to be encrypted.

            :return: A base64 encoded string of the encrypted data. Returns an empty string if encryption fails.
            :raise: Raises an exception if there is an error during encryption, logging the error details.

            setup:
                1. Generate a random IV for encryption.
                2. Create an AES cipher object using the AES key and the generated IV.
                3. Encrypt the data and generate the authentication tag.
                4. Combine the IV, tag, and encrypted data.
                5. Encode the combined data in base64 format.
            """

            try:
                iv = get_random_bytes(12)
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                encrypted_data, tag = aes_cipher.encrypt_and_digest(str(data).encode())
                combined_data = iv + tag + encrypted_data
                return base64.b64encode(combined_data).decode()
            except Exception as e:
                _DefaultLogger.error(f"AES encrypt data error : {e}", exc_info=True)
                return ""

        def decrypt(self, data: str) -> str:
            """
            Decrypts the provided data using AES encryption.

            This method takes a base64 encoded string, decodes it, and uses AES in GCM mode to decrypt the data. It expects the encoded string to contain an initialization vector (IV), an authentication tag, and the encrypted data.

            :param data: The base64 encoded string containing the encrypted data, IV, and tag.

            :return: The decrypted data as a string. Returns an empty string if decryption fails.
            :raise: Raises an exception if there is an error during decryption, logging the error details.

            setup:
                1. Decode the base64 encoded input data.
                2. Extract the IV, tag, and encrypted data from the decoded result.
                3. Create an AES cipher object using the AES key and IV.
                4. Decrypt the encrypted data and verify it against the authentication tag.
            """

            try:
                combined_data = base64.b64decode(data)
                iv = combined_data[:12]
                tag = combined_data[12:28]
                encrypted_data = combined_data[28:]
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                decrypted_data = aes_cipher.decrypt_and_verify(encrypted_data, tag).decode()
                return decrypted_data
            except Exception as e:
                _DefaultLogger.error(f"AES decrypt data error : {e}", exc_info=True)
                return ""


    class RSAEncryptor(_BaseEncryptor):
        """
        RSAEncryptor class for handling RSA encryption and decryption operations.

        The class provides an interface for performing RSA encryption and decryption operations.
        It supports generating RSA key pairs, loading keys from files, and securely encrypting and decrypting data using public and private keys.

        ClassAttributes:
            name: The name of the RSAEncryptor instance.
            identifier: An optional identifier for the RSAEncryptor instance.

        Methods:
            generateRSAKeys: Generates a pair of RSA keys (private and public) and optionally stores them locally.
            loadRSAPrivateKey: Loads a private RSA key from a specified file path.
            loadRSAPublicKey: Loads a public RSA key from a specified file path.
            rsaEncrypt: Encrypts data using the provided public RSA key.
            rsaDecrypt: Decrypts data using the provided private RSA key.
        """

        def __init__(self, name: str, identifier: str = None):
            super().__init__(name, identifier)

        @staticmethod
        def generateRSAKeys(private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple[bytes, bytes] | None:
            """
            Generates a pair of RSA keys (private and public) and optionally stores them in specified file paths.

            This method allows for the creation of RSA keys of varying sizes, defaulting to 2048 bits. The keys can be saved to local files.

            :param private_path: The file path where the private key should be stored. Must be provided if store_locally is True.
            :param public_path: The file path where the public key should be stored. Must be provided if store_locally is True.
            :param key_size: The size of the RSA key to be generated. Options are 1024, 2048, 3072, or 4096 bits. Default is 2048.
            :param store_locally: If True, the generated keys will be saved to the specified file paths.

            :return: A tuple containing the private key and public key in bytes, or None if there was an error during generation or storage.
            :raise: ValueError if the key size is invalid.
            :raise: IOError if there is an issue writing to the specified file paths.

            setup:
                1. Validate the provided key_size, defaulting to 2048 if invalid.
                2. Generate the RSA key pair using RSA.generate.
                3. If store_locally is True, write the public and private keys to the specified file paths.
            """

            if key_size not in [1024, 2048, 3072, 4096]:
                _DefaultLogger.warning(f"Invalid rsa key size: {key_size}. Using default size 2048.")
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                _DefaultLogger.error("RSA keys storage paths not provided.", exc_info=True)
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
            """
            Loads an RSA private key from a specified file path.

            This method reads the private key from a file and imports it into an RSA key object.

            :param private_path: The file path to the private key in bytes format.

            :return: An RSA.RsaKey object if the key is loaded successfully; None otherwise.
            :raise: FileNotFoundError if the specified file does not exist.
            :raise: ValueError if the key format is invalid.

            setup:
                1. Open the file at the given private_path in binary read mode.
                2. Read the private key from the file.
                3. Import the key using RSA.import_key and return the RSA key object.
            """

            try:
                with open(private_path, 'rb') as priv_file:
                    private_key = priv_file.read()
                return RSA.import_key(private_key)
            except Exception as e:
                _DefaultLogger.error(f"Load rsa private key error : {e}", exc_info=True)
                return None

        @staticmethod
        def loadRSAPublicKey(public_path: str) -> RSA.RsaKey:
            """
            Loads an RSA public key from a specified file path.

            This method reads the public key from a file and imports it into an RSA key object.

            :param public_path: The file path to the public key in bytes format.

            :return: An RSA.RsaKey object if the key is loaded successfully; None otherwise.
            :raise: FileNotFoundError if the specified file does not exist.
            :raise: ValueError if the key format is invalid.

            setup:
                1. Open the file at the given public_path in binary read mode.
                2. Read the public key from the file.
                3. Import the key using RSA.import_key and return the RSA key object.
            """

            try:
                with open(public_path, 'rb') as pub_file:
                    public_key = pub_file.read()
                return RSA.import_key(public_key)
            except Exception as e:
                _DefaultLogger.error(f"Load rsa public key error : {e}", exc_info=True)
                return None

        @staticmethod
        def rsaEncrypt(public_key: bytes, data: str) -> bytes:
            """
            Encrypts data using RSA with a given public key.

            This method takes a public RSA key and plaintext data, and returns the encrypted bytes.

            :param public_key: The public RSA key in bytes format.
            :param data: The plaintext data to be encrypted as a string.

            :return: The encrypted data in bytes format.
            :raise: ValueError if encryption fails due to invalid data or key.

            setup:
                1. Import the RSA key using the provided public key bytes.
                2. Create a cipher object using PKCS1_OAEP with the imported public key.
                3. Encrypt the data by encoding it to bytes and passing it to the cipher object.
            """

            public_key_obj = RSA.import_key(public_key)
            cipher_rsa = PKCS1_OAEP.new(public_key_obj)
            encrypted_data = cipher_rsa.encrypt(data.encode())
            return encrypted_data

        @staticmethod
        def rsaDecrypt(private_key: bytes, encrypted_data: bytes) -> str:
            """
            Decrypts data using RSA with a given private key.

            This method takes a private RSA key and encrypted data, and returns the decrypted string.

            :param private_key: The private RSA key in bytes format.
            :param encrypted_data: The encrypted data to be decrypted in bytes format.

            :return: The decrypted data as a string.
            :raise: ValueError if decryption fails due to invalid data or key.

            setup:
                1. Import the RSA key using the provided private key bytes.
                2. Create a cipher object using PKCS1_OAEP with the imported private key.
                3. Decrypt the encrypted data using the cipher object.
            """

            private_key_obj = RSA.import_key(private_key)
            cipher_rsa = PKCS1_OAEP.new(private_key_obj)
            decrypted_data = cipher_rsa.decrypt(encrypted_data)
            return decrypted_data.decode()
except ImportError as _:
    class AESEncryptor:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DefaultLogger.warning("AESEncryptor is not available. Please install keyring, pycryptodome packages.")

        def encrypt(self, data: str) -> str:
            raise NotImplementedError("AESEncryptor is not available. Please install keyring, pycryptodome packages.")

        def decrypt(self, data: str) -> str:
            raise NotImplementedError("AESEncryptor is not available. Please install keyring, pycryptodome packages.")


    class RSAEncryptor:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DefaultLogger.warning("RSAEncryptor is not available. Please install keyring, pycryptodome packages.")

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
