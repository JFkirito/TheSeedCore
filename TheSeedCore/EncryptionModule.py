# -*- coding: utf-8 -*-
"""
TheSeed Encryption Module

# This module provides a comprehensive suite of tools for data encryption and decryption, supporting AES and RSA algorithms.
# It includes classes for performing encryption operations and managing multiple encryptor instances. This module is essential
# for applications requiring secure data handling and communication.
#
# Key Components:
# 1. TheSeedEncryptor: Handles AES encryption/decryption and RSA key pair generation, securely managing keys via a keyring.
# 2. EncryptorManager: Manages multiple TheSeedEncryptor instances, allowing flexible encryption configurations within the application.
#
# Module Functions:
# - Enables AES encryption and decryption of strings.
# - Supports RSA key pair generation with key import/export capabilities.
# - Facilitates encrypted data storage and retrieval, enhancing local security for keys and sensitive data.
# - Integrates detailed logging for tracking encryption and decryption processes, aiding in security audits and troubleshooting.
#
# Usage Scenarios:
# - Encrypting sensitive data for secure storage or transmission in applications.
# - Securing communication between server and client through RSA public key encryption.
# - Locally storing keys or sensitive information with enhanced security.
#
# Dependencies:
# - Crypto.Cipher: Implements AES and RSA encryption algorithms.
# - keyring: Manages secure storage of encryption keys.
# - platform, subprocess: Generate system-based key identifiers.
# - traceback: Captures and logs error information.
# - LoggerModule: Provides logging capabilities for the module.

"""

from __future__ import annotations

__all__ = ["TheSeedEncryptor", "EncryptorManager"]

import base64
import platform
import subprocess
import traceback
from typing import TYPE_CHECKING

import keyring
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger


class TheSeedEncryptor:
    """
    TheSeed加密器。

    参数:
        :param AESName : Keyring 密钥名称。
        :param Logger : 日志记录器。
        :param KeyringIdentifier : Keyring 唯一标识符。

    属性:
        - _AESName : AES密钥名称。
        - _Logger : 日志记录器。
        - _KeyringIdentifier : Keyring 唯一标识符。
        - _AESKey : AES 密钥。
    """

    def __init__(self, AESName: str, Logger: TheSeedCoreLogger, KeyringIdentifier: str = None):
        self._AESName = AESName
        self._Logger = Logger
        self._KeyringIdentifier = self._generateKeyringIdentifier() if KeyringIdentifier is None else KeyringIdentifier
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
            - AES 密钥。
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
            raise e

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
    TheSeed加密管理器。

    参数:
        :param Logger : 日志记录器。

    属性:
        - _INSTANCE : 单例实例。
        - _EncryptorDict (dict): 存储加密管理器实例的字典。
        - _Logger: 日志记录器。
    """

    _INSTANCE: EncryptorManager = None

    def __new__(cls, Logger: TheSeedCoreLogger):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(EncryptorManager, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Logger: TheSeedCoreLogger):
        self._EncryptorDict: dict = {}
        self._Logger = Logger

    def createEncryptor(self, encryptor_name: str, aes_name: str, keyring_identifier: str) -> bool:
        """
        创建一个新的加密器实例并存储在字典中。

        参数:
            :param encryptor_name : 加密器名。
            :param aes_name: 用于检索或存储 AES 密钥的标识符。
            :param keyring_identifier: 用于生成唯一标识符的标识符。
        返回:
            :return 参数不正确时返回 False, 创建成功则返回True。
        """

        if not isinstance(encryptor_name, str):
            self._Logger.error(f"EncryptionManager create encryptor parameter error : encryptor name must be a string.")
            return False
        if not isinstance(aes_name, str):
            self._Logger.error(f"EncryptionManager create encryptor parameter error : keyring name must be a string.")
            return False
        if not isinstance(keyring_identifier, str):
            self._Logger.error(f"EncryptionManager create encryptor parameter error : keyring identifier must be a string.")
            return False
        self._EncryptorDict[encryptor_name] = TheSeedEncryptor(aes_name, self._Logger, keyring_identifier)
        return True

    def getEncryptor(self, encryptor_name: str) -> TheSeedEncryptor | None:
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
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
        encryptor: TheSeedEncryptor = self.getEncryptor(encryptor_name)
        if encryptor and hasattr(encryptor, "rsaDecrypt"):
            return encryptor.rsaDecrypt(private_key, encrypted_data)
        else:
            return None