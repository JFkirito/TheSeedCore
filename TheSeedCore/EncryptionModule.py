# -*- coding: utf-8 -*-
"""
TheSeedCore Encryption Module

Module Description:
This module provides encryption and decryption functionalities using AES and RSA algorithms.
It ensures secure data handling by integrating key management and encryption mechanisms.
The module supports the generation and storage of encryption keys, as well as the encryption and decryption of data.

Main Components:
1. Dependency Check and Import: Checks and imports necessary modules and libraries such as Crypto and keyring.
2. Logger Setup: Configures a default logger for encryption operations to handle logging of operations and errors.
3. Encryptor Configuration: Defines a data class for configuring the encryptor, including AES key names and keyring identifiers.
4. Core Encryptor Class: Implements the core encryption functionalities using AES and RSA, including key generation, data encryption, and decryption.
5. Encryptor Manager: Manages multiple encryptor instances, providing methods for creating, accessing, and using encryptors for various encryption and decryption operations.

Module Functionality Overview:
- Supports AES encryption and decryption with automatic key management using keyring.
- Provides methods to generate and load RSA key pairs, and to perform RSA encryption and decryption.
- Handles secure key storage and retrieval using keyring.
- Provides detailed logging for encryption operations and errors.
- Ensures compatibility with various operating systems for keyring integration.

Key Classes and Methods:
- _checkDependencies(): Checks and imports module dependencies.
- defaultLogger(): Configures and returns a logger for encryption operations.
- EncryptorConfig: Data class for encryptor configuration parameters.
- TheSeedCoreEncryptor: Core class for encryption operations, including AES and RSA encryption/decryption.
- EncryptorManager: Manages multiple encryptor instances and provides methods for encryption and decryption using AES and RSA.

Notes:
- Ensure all necessary dependencies (Crypto, keyring, etc.) are installed before using this module.
- Configure the encryptor parameters appropriately in the EncryptorConfig data class.
- Utilize the EncryptorManager class to handle multiple encryptor instances and ensure proper key management.
- Refer to the logging output for detailed information on encryption operations and errors.
"""

from __future__ import annotations

import base64
import logging
import platform
import subprocess
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

_EncryptSupport = False


def _checkDependencies():
    global _EncryptSupport
    try:
        # noinspection PyUnresolvedReferences
        import keyring
        # noinspection PyUnresolvedReferences
        from Crypto.Cipher import AES, PKCS1_OAEP
        # noinspection PyUnresolvedReferences
        from Crypto.PublicKey import RSA
        # noinspection PyUnresolvedReferences
        from Crypto.Random import get_random_bytes
        _EncryptSupport = True
    except ImportError as _:
        _EncryptSupport = False


_checkDependencies()


def defaultLogger(debug_mode: bool = False) -> logging.Logger:
    logger = logging.getLogger(f'TheSeedCore - Encryptor')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    if debug_mode:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

    formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


if _EncryptSupport:
    # noinspection PyUnresolvedReferences
    import keyring
    # noinspection PyUnresolvedReferences
    from Crypto.Cipher import AES, PKCS1_OAEP
    # noinspection PyUnresolvedReferences
    from Crypto.PublicKey import RSA
    # noinspection PyUnresolvedReferences
    from Crypto.Random import get_random_bytes


    @dataclass
    class EncryptorConfig:
        """
        加密器配置。

        属性:
            - AESName : AES加密器的名称。
            - KeyringIdentifier : 密钥环标识符。
        """
        AESName: str
        KeyringIdentifier: Union[None, str]

        def __post_init__(self):
            if not isinstance(self.AESName, str):
                raise ValueError("The encryptor AES name must be a string.")
            if not isinstance(self.KeyringIdentifier, (str, type(None))):
                raise ValueError("The encryptor keyring identifier must be a string or None.")


    class TheSeedCoreEncryptor:
        """
        TheSeedCore 加密器。

        参数:
            :param Config : 加密器配置。
        属性:
            - _AESName : AES密钥名称。
            - _Logger : 日志记录器。
            - _KeyringIdentifier : Keyring 唯一标识符。
            - _AESKey : AES 密钥。
        """

        def __init__(self, Config: EncryptorConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._AESName = Config.AESName
            self._Logger = defaultLogger(DebugMode) if Logger is None else Logger
            self._KeyringIdentifier = self._generateKeyringIdentifier() if Config.KeyringIdentifier is None else Config.KeyringIdentifier
            self._AESKey = self._loadAESKey()

        def aesEncrypt(self, data: str) -> str:
            """
            AES加密数据。

            参数:
                :param data : 要加密的字符串数据。

            返回:
                :return 加密后的str数据，Base64 编码。
            """
            try:
                iv = get_random_bytes(12)
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                encrypted_data, tag = aes_cipher.encrypt_and_digest(str(data).encode())
                combined_data = iv + tag + encrypted_data
                return base64.b64encode(combined_data).decode()
            except Exception as e:
                error_msg = f"TheSeedEncryptor aes encrypt data error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return ""

        def aesDecrypt(self, encrypted_data: str) -> str:
            """
            AES解密数据。

            参数:
                :param encrypted_data : 加密的 Base64 编码数据。

            返回:
                :return 解密后的字符串数据。
            """
            try:
                combined_data = base64.b64decode(encrypted_data)
                iv = combined_data[:12]
                tag = combined_data[12:28]
                encrypted_data = combined_data[28:]
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                decrypted_data = aes_cipher.decrypt_and_verify(encrypted_data, tag).decode()
                return decrypted_data
            except Exception as e:
                error_msg = f"TheSeedEncryptor decrypt data error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return ""

        def generateRSAKeys(self, private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple[bytes, bytes] | None:
            """
            生成 RSA 密钥对。如果提供的密钥长度无效，将使用默认的 2048 位, 根据 store_locally 参数和 key_size 决定是否保存到文件及密钥的长度。

            参数:
                :param private_path : 私钥存储路径。
                :param public_path : 公钥存储路径。
                :param store_locally : 是否将密钥对存储到本地文件系统。
                :param key_size : RSA 密钥的长度，建议使用 1024, 2048, 3072, 4096 中的一个。

            返回:
                :return (private_key, public_key) 元组。
            """
            if key_size not in [1024, 2048, 3072, 4096]:
                error_message = f"Invalid key size: {key_size}. Using default size 2048."
                self._Logger.error(error_message)
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                self._Logger.error("TheSeedEncryptor generating rsa keys error : storage paths not provided.")
                return None

            key = RSA.generate(key_size)
            private_key = key.export_key()
            public_key = key.publickey().export_key()

            if store_locally:
                with open(public_path, 'wb') as pub_file:
                    pub_file.write(public_key)
                encrypted_private_key = self.aesEncrypt(private_key.decode('utf-8'))
                with open(private_path, 'wb') as priv_file:
                    priv_file.write(encrypted_private_key.encode())
            return private_key, public_key

        def loadRSAPrivateKey(self, private_path: str) -> RSA:
            """
            从指定路径加载并解密 RSA 私钥。

            参数:
                :param private_path : 私钥存储路径。

            返回:
                :return RSA 私钥对象。
            """
            try:
                with open(private_path, 'rb') as priv_file:
                    encrypted_private_key = priv_file.read()
                decrypted_private_key = self.aesDecrypt(encrypted_private_key.decode())
                return RSA.import_key(decrypted_private_key.encode())
            except Exception as e:
                self._Logger.error(f"TheSeedEncryptor loading rsa private key error : {str(e)}")
                return None

        def loadRSAPublicKey(self, public_path: str) -> RSA:
            """
            从指定路径加载 RSA 公钥。

            参数:
                :param public_path : 公钥存储路径。

            返回:
                :return RSA 公钥对象。
            """
            try:
                with open(public_path, 'rb') as pub_file:
                    public_key = pub_file.read()
                return RSA.import_key(public_key)
            except Exception as e:
                self._Logger.error(f"TheSeedEncryptor loading rsa public key error : {str(e)}")
                return None

        @staticmethod
        def rsaEncrypt(public_key: bytes, data: str) -> bytes:
            """
            使用 RSA 公钥加密数据。

            参数:
                :param public_key : 公钥的字节串。
                :param data : 要加密的字符串数据。

            返回:
                :return 加密后的字节数据。
            """
            public_key_obj = RSA.import_key(public_key)
            cipher_rsa = PKCS1_OAEP.new(public_key_obj)
            encrypted_data = cipher_rsa.encrypt(data.encode())
            return encrypted_data

        @staticmethod
        def rsaDecrypt(private_key: bytes, encrypted_data: bytes) -> str:
            """
            使用 RSA 私钥解密数据。

            参数:
                :param private_key : 私钥的字节串。
                :param encrypted_data : 加密的字节数据。

            返回:
                :return 解密后的字符串数据。
            """
            private_key_obj = RSA.import_key(private_key)
            cipher_rsa = PKCS1_OAEP.new(private_key_obj)
            decrypted_data = cipher_rsa.decrypt(encrypted_data)
            return decrypted_data.decode()

        def _generateKeyringIdentifier(self) -> str:
            """根据操作系统类型生成一个唯一的Keyring标识符。"""
            try:
                os_type = platform.system()
                if os_type == "Windows":
                    manufacturer = subprocess.check_output("wmic baseboard get Manufacturer", shell=True).decode().split('\n')[1].strip()
                    product = subprocess.check_output("wmic baseboard get Product", shell=True).decode().split('\n')[1].strip()
                    serial_number = subprocess.check_output("wmic baseboard get SerialNumber", shell=True).decode().split('\n')[1].strip()
                    key_name = f"{self._AESName} - {manufacturer} - {product} - {serial_number}"
                elif os_type == "Darwin":
                    info = subprocess.check_output(["system_profiler", "SPHardwareDataType"]).decode()
                    lines = info.split('\n')
                    serial_line = next((line for line in lines if "Serial Number (system)" in line), None)
                    serial_number = serial_line.split(':')[1].strip() if serial_line else "UnknownSerial"
                    manufacturer = "Apple"
                    key_name = f"{self._AESName} - {manufacturer} - {serial_number}"
                else:
                    error_msg = f"TheSeedEncryptor generate keyring identifier error : Unsupported OS type."
                    self._Logger.error(error_msg)
                    return f"{self._AESName}"
                return key_name
            except Exception as e:
                error_msg = f"TheSeedEncryptor generate keyring identifier error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return f"{self._AESName}"

        def _loadAESKey(self) -> bytes | None:
            """
            从 keyring 中加载 AES 密钥，如果不存在则生成新密钥并存储。

            返回:
                :return : AES 密钥。
            """
            try:
                encoded_key = keyring.get_password(self._KeyringIdentifier, self._AESName)
                if encoded_key:
                    return base64.b64decode(encoded_key)
                else:
                    aes_key = get_random_bytes(32)
                    self._saveAESKey(aes_key)
                    return aes_key
            except Exception as e:
                error_msg = f"TheSeedEncryptor load aes key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)

        def _saveAESKey(self, key):
            """
            保存 AES 密钥。

            参数:
                :param key : 要保存的 AES 密钥。
            """
            try:
                encoded_key = base64.b64encode(key).decode("utf-8")
                keyring.set_password(self._KeyringIdentifier, self._AESName, encoded_key)
            except Exception as e:
                error_msg = f"TheSeedEncryptor save aes key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)


    class EncryptorManager:
        """
        TheSeedCore 加密管理器。

        参数:
            :param Logger : 日志记录器。

        属性:
            - _INSTANCE : 单例实例。
            - _EncryptorDict (dict): 存储加密管理器实例的字典。
            - _Logger: 日志记录器。
        """

        _INSTANCE: EncryptorManager = None

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if cls._INSTANCE is None:
                cls._INSTANCE = super(EncryptorManager, cls).__new__(cls)
            return cls._INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._EncryptorDict: dict = {}
            self._Logger = defaultLogger(DebugMode) if Logger is None else Logger

        def createEncryptor(self, encryptor_name: str, config: EncryptorConfig, logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False) -> bool:
            """
            创建一个新的加密器实例并存储在字典中。

            参数:
                :param encryptor_name : 加密器名。
                :param config : 加密器配置。
                :param logger : 日志记录器。
                :param debug_mode : 是否启用调试模式。
            返回:
                :return 是否成功创建加密器。
            """
            if encryptor_name in self._EncryptorDict:
                self._Logger.warning(f"EncryptionManager create encryptor warning : encryptor {encryptor_name} already exists.")
                return False
            self._EncryptorDict[encryptor_name] = TheSeedCoreEncryptor(config, logger, debug_mode)
            return True

        def getEncryptor(self, encryptor_name: str) -> TheSeedCoreEncryptor | None:
            """
            根据加密器名获取对应的加密器实例。

            参数:
                :param encryptor_name : 加密器名。

            返回:
                :return TheSeedEncryptor : 对应的加密管理器实例，如果不存在则返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager get encryptor instance parameter error : encryptor name must be a string.")
                return
            return self._EncryptorDict[encryptor_name]

        def aesEncryptData(self, encryptor_name: str, data: str) -> str | None:
            """
            使用指定的加密器加密数据。

            参数:
                :param encryptor_name : 加密管理器的键。
                :param data : 需要加密的字符串数据。

            返回:
                :return 加密后的数据，如果加密器不存在或参数错误则返回 None。

            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager aes encrypt data parameter error : encryptor name must be a string.")
                return None
            if not isinstance(data, str):
                self._Logger.error(f"EncryptionManager aes encrypt data parameter error : data must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "aesEncryptData"):
                return encryptor.aesEncrypt(data)
            else:
                return None

        def aesDecryptData(self, encryptor_name: str, data: str) -> str | None:
            """
            使用指定的加密器解密数据。

            参数:
                :param encryptor_name : 加密管理器的键。
                :param data : 需要解密的数据。

            返回:
                :return  解密后的数据，如果加密器不存在或参数错误则返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager decrypt data parameter error : encryptor name must be a string.")
                return None
            if not isinstance(data, str):
                self._Logger.error(f"EncryptionManager decrypt data parameter error : data must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "aesDecryptData"):
                return encryptor.aesDecrypt(data)
            else:
                return None

        def generateRSAKeys(self, encryptor_name: str, private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple | None:
            """
            生成 RSA 密钥对。

            参数:
                :param encryptor_name : 加密管理器的键。
                :param private_path : 私钥存储路径。
                :param public_path : 公钥存储路径。
                :param key_size : RSA 密钥的长度。
                :param store_locally : 是否将密钥对存储到本地文件系统。

            返回:
                :return 如果不存储到本地，则返回 (private_key, public_key) 元组。
            """

            if key_size not in [1024, 2048, 3072, 4096]:
                error_message = f"Invalid key size: {key_size}. Using default size 2048."
                self._Logger.error(error_message)
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                self._Logger.error(f"EncryptionManager generating rsa keys error : storage paths not provided.")
                return None

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager generating rsa keys parameter error : encryptor name must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "generateRSAKeys"):
                return encryptor.generateRSAKeys(private_path, public_path, key_size, store_locally)
            else:
                return None

        def loadRSAPrivateKey(self, encryptor_name: str, private_path: str) -> RSA:
            """
            从指定路径加载并解密 RSA 私钥。

            参数:
                :param encryptor_name : 加密管理器的键。
                :param private_path : 私钥存储路径。

            返回:
                :return 返回 RSA 私钥对象。
            """
            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager load private key parameter error : encryptor name must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "loadRSAPrivateKey"):
                return encryptor.loadRSAPrivateKey(private_path)
            else:
                return None

        def loadRSAPublicKey(self, encryptor_name: str, public_path) -> RSA:
            """
            从指定路径加载 RSA 公钥。

            参数:
                :param encryptor_name : 加密器名。
                :param public_path : 公钥存储路径。

            返回:
                :return 返回 RSA 公钥对象。
            """
            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager load public key parameter error : encryptor name must be a string.")
                return
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "loadRSAPublicKey"):
                return encryptor.loadRSAPublicKey(public_path)
            else:
                return

        def rsaEncrypt(self, encryptor_name: str, public_key: bytes, data: str) -> bytes | None:
            """
            使用 RSA 公钥加密数据。

            参数:
                :param encryptor_name: 加密器名。
                :param public_key: 公钥的字节串。
                :param data: 要加密的字符串数据。

            返回:
                :return 加密后的字节数据。
            """
            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager rsa encrypt parameter error : encryptor name must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "rsaEncrypt"):
                return encryptor.rsaEncrypt(public_key, data)
            else:
                return None

        def rsaDecrypt(self, encryptor_name: str, private_key: bytes, encrypted_data: bytes) -> str | None:
            """
            使用 RSA 私钥解密数据。

            参数:
                :param encryptor_name : 加密器名。
                :param private_key : 私钥的字节串。
                :param encrypted_data : 加密的字节数据。

            返回:
                :return 解密后的字符串数据。
            """
            if not isinstance(encryptor_name, str):
                self._Logger.error(f"EncryptionManager rsa decrypt parameter error : encryptor name must be a string.")
                return None
            encryptor: TheSeedCoreEncryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "rsaDecrypt"):
                return encryptor.rsaDecrypt(private_key, encrypted_data)
            else:
                return None
