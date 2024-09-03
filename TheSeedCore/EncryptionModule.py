# -*- coding: utf-8 -*-
"""
TheSeedCore EncryptionModule

######################################################################################################################################
# This module provides encryption and decryption utilities to secure sensitive data within the application.
# It supports various encryption algorithms and manages encryption keys, ensuring data confidentiality
# and integrity. The module is designed to be easily integrated with other modules, such as DatabaseModule.py,
# to provide seamless data protection across different components of the system.

# Main functionalities:
# 1. Encrypt data using symmetric and asymmetric encryption algorithms.
# 2. Decrypt previously encrypted data.
# 3. Manage encryption keys, including generation, storage, and retrieval.
# 4. Support for multiple encryption standards (e.g., AES, RSA).
# 5. Provide utility functions for hashing and verifying data integrity.
# 6. Integrate with logging utilities to monitor encryption and decryption operations.

# Main components:
# 1. Encryptor - A class that handles encryption and decryption processes using specified algorithms.
# 2. KeyManager - A class responsible for generating, storing, and retrieving encryption keys securely.
# 3. HashUtil - A utility class that provides hashing functions for data integrity verification.
# 4. Configuration classes - Define settings for encryption algorithms, key lengths, and other parameters.
# 5. Exception classes - Custom exceptions for handling encryption-related errors.

# Design thoughts:
# 1. Security-first approach:
#    a. The module prioritizes the security of data by implementing robust encryption standards.
#    b. Key management is handled with utmost care to prevent unauthorized access and ensure key integrity.
#
# 2. Flexibility and extensibility:
#    a. Supports multiple encryption algorithms, allowing the application to switch or upgrade encryption methods as needed.
#    b. Designed to be easily extendable to incorporate additional encryption techniques in the future.
#
# 3. Seamless integration:
#    a. The module is designed to integrate smoothly with other modules, such as DatabaseModule.py, enabling automatic encryption and decryption of data during storage and retrieval.
#    b. Provides a simple and consistent interface for encryption operations, minimizing the learning curve for developers.
#
# 4. Performance optimization:
#    a. Implements efficient encryption algorithms to minimize performance overhead.
#    b. Utilizes caching mechanisms for frequently used keys to reduce latency in encryption and decryption processes.
#
# 5. Comprehensive error handling:
#    a. Incorporates detailed exception handling to manage and log encryption-related errors effectively.
#    b. Ensures that failures in encryption processes do not compromise the application's stability or data integrity.
#
# 6. Compliance and best practices:
#    a. Adheres to industry standards and best practices for encryption and data security.
#    b. Regularly updates encryption methodologies to comply with evolving security requirements and threats.

# Required dependencies:
# 1. Python libraries: cryptography, hashlib, logging, os, base64.
# 2. Optional libraries for advanced encryption features: PyCryptodome, bcrypt.
######################################################################################################################################
"""

from __future__ import annotations

__all__ = [
    "EncryptorConfig",
    "Encryptor",
    "EncryptorManager",
    "EncryptSupport"
]

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

EncryptSupport = False


def defaultLogger(debug_mode: bool = False) -> logging.Logger:
    """
    创建并配置一个默认的 `logging.Logger` 实例，用于日志记录。

    参数：
        :param debug_mode: 是否启用调试模式。如果为 `True`，日志级别设置为 `DEBUG`，否则设置为 `WARNING` 和 `DEBUG` 中的较高级别。

    返回：
        :return - logging.Logger: 配置好的 `Logger` 实例。

    执行过程：
        1. 创建一个 `Logger` 实例，并设置其日志级别为 `DEBUG`。
        2. 创建一个 `StreamHandler` 实例，用于将日志输出到控制台。
        3. 根据 `debug_mode` 参数设置控制台处理器的日志级别：
            a. 如果 `debug_mode` 为 `True`，日志级别设置为 `DEBUG`。
            b. 如果 `debug_mode` 为 `False`，日志级别设置为 `WARNING` 和 `DEBUG` 中的较高级别。
        4. 配置日志格式化器 `_ColoredFormatter` 并将其设置到控制台处理器上。
        5. 将控制台处理器添加到 `Logger` 实例中。

    异常：
        1. 无特殊异常处理，所有配置过程均由标准库功能处理。
    """

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


@dataclass
class EncryptorConfig:
    """
    EncryptorConfig 加密器配置，包括 AES 名称和 Keyring 标识符。

    参数：
        :param AESName: AES 加密算法的名称，必须是字符串。
        :param KeyringIdentifier: Keyring标识符，可以是字符串或者 None。

    属性：
        - AESName: AES 加密算法的名称。
        - KeyringIdentifier: Keyring标识符，可以是字符串或者 None。

    设计思路：
        1. 确保 AESName 和 KeyringIdentifier 参数类型的正确性。
            a. AESName 必须是字符串。
            b. KeyringIdentifier 必须是字符串或 None。

    异常：
        1. 如果 AESName 不是字符串，则抛出 ValueError 异常。
        2. 如果 KeyringIdentifier 既不是字符串也不是 None，则抛出 ValueError 异常。
    """
    AESName: str
    KeyringIdentifier: Union[None, str]

    def __post_init__(self):
        if not isinstance(self.AESName, str):
            raise ValueError("The encryptor AES name must be a string.")
        if not isinstance(self.KeyringIdentifier, (str, type(None))):
            raise ValueError("The encryptor keyring identifier must be a string or None.")


# Try defining the Encryptor class and the EncryptorManager class.
try:
    # noinspection PyUnresolvedReferences
    import keyring
    # noinspection PyUnresolvedReferences
    from Crypto.Cipher import AES, PKCS1_OAEP
    # noinspection PyUnresolvedReferences
    from Crypto.PublicKey import RSA
    # noinspection PyUnresolvedReferences
    from Crypto.Random import get_random_bytes
except ImportError:
    class Encryptor:
        # noinspection PyUnusedLocal
        def __init__(self, Config: EncryptorConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The keyring and pycryptodome are not installed. Please install them using 'pip install keyring pycryptodome'.")


    class EncryptorManager:
        # noinspection PyUnusedLocal
        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The keyring and pycryptodome are not installed. Please install them using 'pip install keyring pycryptodome'.")
else:
    EncryptSupport = True


    class Encryptor:
        """
        加密器基类，提供对称 AES 加密和解密、RSA 密钥生成、存储和加载功能，以及密钥环标识符的生成。

        参数：
            :param Config: EncryptorConfig 对象，包含 AES 加密名称和密钥环标识符。
            :param Logger: 可选参数，用于日志记录。可以是 TheSeedCoreLogger 或 logging.Logger 对象，默认为 None。
            :param DebugMode: 可选参数，布尔值，指示是否启用调试模式，默认为 False。

        属性：
            - _AESName: 从配置中获取的 AES 加密算法名称。
            - _Logger: 用于日志记录的 Logger 对象。
            - _KeyringIdentifier: 密钥环标识符。
            - _AESKey: 加载或生成的 AES 密钥。

        设计思路：
            1. 初始化 Encryptor 对象时，根据提供的配置设置 AES 名称、密钥环标识符，并加载 AES 密钥。
            2. 提供方法进行 AES 加密和解密，使用 AES-GCM 模式。
            3. 提供方法生成 RSA 密钥对，并可选择将密钥存储在本地。
            4. 提供方法加载 RSA 密钥对。
            5. 使用密钥环标识符生成唯一的密钥环标识符。
            6. 加载和保存 AES 密钥，使用密钥环服务进行管理。

        异常：
            1. 在加密或解密过程中，如果发生异常，则记录错误日志并返回空字符串。
            2. 生成 RSA 密钥对时，如果存储路径未提供，则记录错误日志并返回 None。
            3. 加载或保存 RSA 密钥和 AES 密钥时，如果发生异常，则记录错误日志并返回 None。
            4. 生成密钥环标识符时，如果发生异常，则记录错误日志并返回默认名称。
        """

        def __init__(self, Config: EncryptorConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._AESName = Config.AESName
            self._Logger = defaultLogger(DebugMode) if Logger is None else Logger
            self._KeyringIdentifier = self._generateKeyringIdentifier() if Config.KeyringIdentifier is None else Config.KeyringIdentifier
            self._AESKey = self._loadAESKey()

        def aesEncrypt(self, data: str) -> str:
            """
            使用 AES-GCM 模式对输入数据进行加密，并返回加密后的 Base64 编码字符串。

            参数：
                :param data: 需要加密的字符串数据。

            返回：
                :return - str: 加密后的 Base64 编码字符串。如果加密过程中发生异常，返回空字符串。

            执行过程：
                1. 生成一个 12 字节的随机初始化向量 (IV)。
                2. 使用 AES-GCM 模式和生成的 IV 创建 AES 加密器对象。
                3. 对输入数据进行加密，并生成加密标签 (tag)。
                4. 将 IV、标签和加密后的数据组合在一起。
                5. 对组合数据进行 Base64 编码，并将其解码为字符串返回。

            异常：
                1. 捕获所有异常，并记录错误信息到日志中。返回空字符串。
            """

            try:
                iv = get_random_bytes(12)
                aes_cipher = AES.new(self._AESKey, AES.MODE_GCM, iv)
                encrypted_data, tag = aes_cipher.encrypt_and_digest(str(data).encode())
                combined_data = iv + tag + encrypted_data
                return base64.b64encode(combined_data).decode()
            except Exception as e:
                self._Logger.error(f"AES encrypt data error : {e}\n\n{traceback.format_exc()}")
                return ""

        def aesDecrypt(self, encrypted_data: str) -> str:
            """
            使用 AES-GCM 模式对加密数据进行解密，并返回解密后的原始字符串数据。

            参数：
                :param encrypted_data: 需要解密的 Base64 编码加密字符串。

            返回：
                :return - str: 解密后的原始字符串数据。如果解密过程中发生异常，返回空字符串。

            执行过程：
                1. 对输入的 Base64 编码加密字符串进行解码，得到组合数据。
                2. 从组合数据中提取初始化向量 (IV)、加密标签 (tag) 和加密数据。
                3. 使用 AES-GCM 模式、提取的 IV 和 AES 密钥创建 AES 解密器对象。
                4. 对加密数据进行解密，并使用标签进行验证，得到解密后的数据。
                5. 将解密后的数据解码为字符串并返回。

            异常：
                1. 捕获所有异常，并记录错误信息到日志中。返回空字符串。
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
                self._Logger.error(f"AES decrypt data error : {e}\n\n{traceback.format_exc()}")
                return ""

        def generateRSAKeys(self, private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple[bytes, bytes] | None:
            """
            生成 RSA 密钥对，并根据参数选择是否将密钥存储到本地文件。

            参数：
                :param private_path: 私钥文件的存储路径。如果不需要存储私钥，可设置为 None。
                :param public_path: 公钥文件的存储路径。如果不需要存储公钥，可设置为 None。
                :param key_size: 生成密钥的大小，单位为位。可选值为 1024, 2048, 3072, 4096。默认值为 2048。
                :param store_locally: 是否将密钥存储到本地文件。默认值为 False。

            返回：
                :return - tuple[bytes, bytes] | None: 返回生成的私钥和公钥的字节串。如果存储路径无效或未提供，则返回 None。

            执行过程：
                1. 验证密钥大小是否有效，若无效则使用默认值 2048。
                2. 检查是否选择了本地存储密钥，如果选择了存储，则确保提供了私钥和公钥的路径。
                3. 使用指定的密钥大小生成 RSA 密钥对。
                4. 将生成的私钥和公钥导出为字节串。
                5. 如果选择了存储密钥：
                    a. 将公钥保存到指定路径的文件中。
                    b. 使用 AES 加密私钥，并将加密后的私钥保存到指定路径的文件中。
                6. 返回私钥和公钥的字节串。

            异常：
                1. 如果密钥大小无效，则记录警告日志，并使用默认大小 2048。
                2. 如果选择存储本地密钥但未提供路径，则记录错误日志，并返回 None。
            """

            if key_size not in [1024, 2048, 3072, 4096]:
                self._Logger.warning(f"Invalid key size: {key_size}. Using default size 2048.")
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                self._Logger.error("Generating RSA keys error : storage paths not provided.")
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
            从本地文件加载加密的 RSA 私钥，并进行解密以返回 RSA 密钥对象。

            参数：
                :param private_path: 存储加密私钥的文件路径。

            返回：
                :return - RSA | None: 返回解密后的 RSA 私钥对象。如果加载或解密过程出现错误，则返回 None。

            执行过程：
                1. 打开并读取指定路径的加密私钥文件。
                2. 解密读取到的加密私钥数据。
                3. 使用解密后的私钥数据导入并返回 RSA 密钥对象。

            异常：
                1. 如果在读取文件或解密过程中出现错误，则记录错误日志，并返回 None。
            """

            try:
                with open(private_path, 'rb') as priv_file:
                    encrypted_private_key = priv_file.read()
                decrypted_private_key = self.aesDecrypt(encrypted_private_key.decode())
                return RSA.import_key(decrypted_private_key.encode())
            except Exception as e:
                self._Logger.error(f"Load RSA private key error : {str(e)}")
                return None

        def loadRSAPublicKey(self, public_path: str) -> RSA:
            """
            从本地文件加载 RSA 公钥，并返回 RSA 密钥对象。

            参数：
                :param public_path: 存储 RSA 公钥的文件路径。

            返回：
                :return - RSA | None: 返回导入的 RSA 公钥对象。如果加载过程出现错误，则返回 None。

            执行过程：
                1. 打开并读取指定路径的 RSA 公钥文件。
                2. 使用读取到的公钥数据导入并返回 RSA 密钥对象。

            异常：
                1. 如果在读取文件或导入过程中出现错误，则记录错误日志，并返回 None。
            """

            try:
                with open(public_path, 'rb') as pub_file:
                    public_key = pub_file.read()
                return RSA.import_key(public_key)
            except Exception as e:
                self._Logger.error(f"Load RSA public key error : {str(e)}")
                return None

        @staticmethod
        def rsaEncrypt(public_key: bytes, data: str) -> bytes:
            """
            使用 RSA 公钥加密数据，并返回加密后的字节数据。

            参数：
                :param public_key: RSA 公钥，格式为字节数据。
                :param data: 需要加密的明文数据。

            返回：
                :return - bytes: 返回加密后的数据字节流。

            执行过程：
                1. 从字节数据中导入 RSA 公钥。
                2. 使用公钥初始化 RSA 加密器。
                3. 使用 RSA 加密器对数据进行加密。

            异常：
                1. 如果在导入公钥或加密数据过程中出现错误，则会引发异常。
            """

            public_key_obj = RSA.import_key(public_key)
            cipher_rsa = PKCS1_OAEP.new(public_key_obj)
            encrypted_data = cipher_rsa.encrypt(data.encode())
            return encrypted_data

        @staticmethod
        def rsaDecrypt(private_key: bytes, encrypted_data: bytes) -> str:
            """
            使用 RSA 私钥解密数据，并返回解密后的明文字符串。

            参数：
                :param private_key: RSA 私钥，格式为字节数据。
                :param encrypted_data: 需要解密的加密数据，格式为字节数据。

            返回：
                :return - str: 返回解密后的明文数据。

            执行过程：
                1. 从字节数据中导入 RSA 私钥。
                2. 使用私钥初始化 RSA 解密器。
                3. 使用 RSA 解密器对加密数据进行解密。
                4. 将解密后的数据解码为字符串并返回。

            异常：
                1. 如果在导入私钥或解密数据过程中出现错误，则会引发异常。
            """

            private_key_obj = RSA.import_key(private_key)
            cipher_rsa = PKCS1_OAEP.new(private_key_obj)
            decrypted_data = cipher_rsa.decrypt(encrypted_data)
            return decrypted_data.decode()

        def _generateKeyringIdentifier(self) -> str:
            """
            生成唯一的Keyring标识符，根据操作系统类型提取系统信息以创建标识符。

            参数：
                无

            返回：
                :return - str: 生成的密钥环标识符字符串。

            执行过程：
                1. 检查操作系统类型（Windows、macOS 或其他）。
                2. 对于 Windows 系统：
                    a. 使用 `wmic` 命令获取主板制造商、产品型号和序列号。
                    b. 将这些信息组合成密钥环标识符。
                3. 对于 macOS 系统：
                    a. 使用 `system_profiler` 命令获取系统硬件信息。
                    b. 从中提取序列号，并将其与制造商（Apple）组合成密钥环标识符。
                4. 对于其他操作系统，记录错误并返回默认的密钥环标识符。

            异常：
                1. 如果在获取系统信息或生成标识符过程中出现错误，则会记录错误并返回默认的密钥环标识符。
            """

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
                    self._Logger.error(f"Generate keyring identifier error : Unsupported OS type.")
                    return f"{self._AESName}"
                return key_name
            except Exception as e:
                self._Logger.error(f"Generate keyring identifier error : {e}\n\n{traceback.format_exc()}")
                return f"{self._AESName}"

        def _loadAESKey(self) -> bytes | None:
            """
            从密钥环中加载 AES 密钥。如果密钥不存在，则生成一个新的 AES 密钥并保存到密钥环中。

            参数：
                无

            返回：
                :return - bytes | None: 解码后的 AES 密钥字节，或者如果发生错误则返回 None。

            执行过程：
                1. 尝试从密钥环中获取编码的 AES 密钥。
                2. 如果获取到密钥，则解码并返回。
                3. 如果获取不到密钥，则生成一个新的 AES 密钥：
                    a. 使用 `get_random_bytes` 生成 32 字节的 AES 密钥。
                    b. 调用 `_saveAESKey` 方法将生成的密钥保存到密钥环中。
                    c. 返回生成的 AES 密钥。
                4. 如果在过程中发生异常，记录错误并返回 None。

            异常：
                1. 捕获所有异常，记录错误信息。
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
                error_msg = f"Load AES key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)

        def _saveAESKey(self, key):
            """
            将 AES 密钥保存到密钥环中。

            参数：
                :param - key: 要保存的 AES 密钥字节。

            返回：
                :return - None: 无返回值。

            执行过程：
                1. 将 AES 密钥进行 base64 编码以便存储。
                2. 使用 `keyring.set_password` 将编码后的密钥保存到密钥环中。

            异常：
                1. 捕获所有异常，记录错误信息。
            """

            try:
                encoded_key = base64.b64encode(key).decode("utf-8")
                keyring.set_password(self._KeyringIdentifier, self._AESName, encoded_key)
            except Exception as e:
                error_msg = f"Save AES key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)


    class EncryptorManager:
        """
        加密器管理器，创建、管理和操作多个 Encryptor 实例，支持 AES 和 RSA 加密操作。

        参数：
            :param Logger: 可选参数，用于日志记录。可以是 TheSeedCoreLogger 或 logging.Logger 对象，默认为 None。
            :param DebugMode: 可选参数，布尔值，指示是否启用调试模式，默认为 False。

        属性：
            - _EncryptorDict: 存储 Encryptor 实例的字典。
            - _Logger: 用于日志记录的 Logger 对象。

        设计思路：
            1. 通过 __new__ 方法确保 EncryptorManager 为单例模式。
            2. 使用 __init__ 方法初始化 EncryptorDict 和 Logger。
            3. 提供方法创建 Encryptor 实例，并将其存储在字典中。
            4. 提供方法获取指定的 Encryptor 实例。
            5. 提供 AES 加密和解密数据的方法。
            6. 提供生成 RSA 密钥对、加载 RSA 私钥和公钥的方法。
            7. 提供 RSA 加密和解密数据的方法。

        异常：
            1. 如果 Encryptor 实例已经存在，则创建 Encryptor 时记录警告日志并返回 False。
            2. 获取 Encryptor 实例时，如果参数错误或实例不存在，则记录错误日志并返回 None。
            3. 在加密或解密过程中，如果参数错误或 Encryptor 实例没有相应的方法，则记录错误日志并返回 None。
            4. 在生成 RSA 密钥对时，如果参数错误或存储路径未提供，则记录错误日志并返回 None。
            5. 加载 RSA 密钥时，如果发生异常，则记录错误日志并返回 None。
        """
        _INSTANCE: EncryptorManager = None

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if cls._INSTANCE is None:
                # noinspection PySuperArguments
                cls._INSTANCE = super(EncryptorManager, cls).__new__(cls)
            return cls._INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._EncryptorDict: dict = {}
            self._Logger = defaultLogger(DebugMode) if Logger is None else Logger

        def createEncryptor(self, encryptor_name: str, config: EncryptorConfig, logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False) -> bool:
            """
            创建一个新的加密器并将其添加到加密器字典中。

            参数：
                :param - encryptor_name: 加密器的名称。
                :param - config: 加密器的配置对象。
                :param - logger: 可选的日志记录器对象，默认为 None。
                :param - debug_mode: 可选的调试模式标志，默认为 False。

            返回：
                :return - bool: 如果加密器创建成功，则返回 True；如果加密器已存在，则返回 False。

            执行过程：
                1. 检查加密器字典中是否已经存在指定名称的加密器。
                2. 如果加密器已存在，记录警告并返回 False。
                3. 如果加密器不存在，创建一个新的加密器对象并将其添加到字典中。

            异常：
                1. 无显式异常处理，创建加密器失败时可能抛出异常。
            """

            if encryptor_name in self._EncryptorDict:
                self._Logger.warning(f"Create encryptor warning : encryptor {encryptor_name} already exists.")
                return False
            self._EncryptorDict[encryptor_name] = Encryptor(config, logger, debug_mode)
            return True

        def getEncryptor(self, encryptor_name: str) -> Encryptor | None:
            """
            根据名称获取加密器实例。

            参数：
                :param - encryptor_name: 加密器的名称。

            返回：
                :return - Encryptor | None: 返回指定名称的加密器实例，如果未找到或名称参数无效，则返回 None。

            执行过程：
                1. 检查传入的加密器名称是否为字符串。
                2. 如果名称参数无效，记录错误并返回 None。
                3. 如果名称参数有效，从加密器字典中获取对应的加密器实例。

            异常：
                1. 无显式异常处理，若加密器名称不在字典中，返回值为 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"Get encryptor instance parameter error : encryptor name must be a string.")
                return
            return self._EncryptorDict[encryptor_name]

        def aesEncryptData(self, encryptor_name: str, data: str) -> str | None:
            """
            使用指定的加密器名称对数据进行 AES 加密。

            参数：
                :param - encryptor_name: 加密器的名称。
                :param - data: 需要加密的数据，必须是字符串类型。

            返回：
                :return - str | None: 返回加密后的数据，如果加密器名称无效、数据类型错误或加密失败，则返回 None。

            执行过程：
                1. 检查传入的加密器名称是否为字符串，若无效则记录错误并返回 None。
                2. 检查传入的数据是否为字符串，若无效则记录错误并返回 None。
                3. 从加密器字典中获取指定名称的加密器实例。
                4. 如果找到加密器且其具有 `aesEncryptData` 方法，使用该方法对数据进行加密并返回结果。
                5. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效或数据类型错误，记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"AES encrypt data parameter error : encryptor name must be a string.")
                return None
            if not isinstance(data, str):
                self._Logger.error(f"AES encrypt data parameter error : data must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "aesEncryptData"):
                return encryptor.aesEncrypt(data)
            else:
                return None

        def aesDecryptData(self, encryptor_name: str, data: str) -> str | None:
            """
            使用指定的加密器名称对数据进行 AES 解密。

            参数：
                :param - encryptor_name: 加密器的名称。
                :param - data: 需要解密的数据，必须是字符串类型。

            返回：
                :return - str | None: 返回解密后的数据，如果加密器名称无效、数据类型错误或解密失败，则返回 None。

            执行过程：
                1. 检查传入的加密器名称是否为字符串，若无效则记录错误并返回 None。
                2. 检查传入的数据是否为字符串，若无效则记录错误并返回 None。
                3. 从加密器字典中获取指定名称的加密器实例。
                4. 如果找到加密器且其具有 `aesDecryptData` 方法，使用该方法对数据进行解密并返回结果。
                5. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效或数据类型错误，记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"AES decrypt data parameter error : encryptor name must be a string.")
                return None
            if not isinstance(data, str):
                self._Logger.error(f"AES decrypt data parameter error : data must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "aesDecryptData"):
                return encryptor.aesDecrypt(data)
            else:
                return None

        def generateRSAKeys(self, encryptor_name: str, private_path: str = None, public_path: str = None, key_size=2048, store_locally=False) -> tuple | None:
            """
            使用指定的加密器名称生成 RSA 密钥对，并可选择将其保存到本地文件。

            参数：
                :param - encryptor_name: 加密器的名称，必须是字符串类型。
                :param - private_path: 私钥保存的路径，如果 `store_locally` 为 True 时必须提供。
                :param - public_path: 公钥保存的路径，如果 `store_locally` 为 True 时必须提供。
                :param - key_size: RSA 密钥的大小，支持的值为 1024、2048、3072、4096，默认为 2048。
                :param - store_locally: 是否将密钥保存到本地，默认为 False。

            返回：
                :return - tuple | None: 返回一个包含私钥和公钥的元组，如果发生错误或密钥生成失败，则返回 None。

            执行过程：
                1. 验证密钥大小是否有效，若无效则使用默认大小 2048，并记录错误。
                2. 如果选择将密钥保存到本地，则检查私钥和公钥的路径是否提供，若未提供则记录错误并返回 None。
                3. 检查加密器名称是否为字符串，若无效则记录错误并返回 None。
                4. 从加密器字典中获取指定名称的加密器实例。
                5. 如果找到加密器且其具有 `generateRSAKeys` 方法，使用该方法生成 RSA 密钥对并返回结果。
                6. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效、路径未提供或密钥生成失败，记录错误并返回 None。
            """

            if key_size not in [1024, 2048, 3072, 4096]:
                error_message = f"Invalid key size: {key_size}. Using default size 2048."
                self._Logger.error(error_message)
                key_size = 2048

            if store_locally and (not private_path or not public_path):
                self._Logger.error(f"Generating RSA keys error : storage paths not provided.")
                return None

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"Generating RSA keys parameter error : encryptor name must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "generateRSAKeys"):
                return encryptor.generateRSAKeys(private_path, public_path, key_size, store_locally)
            else:
                return None

        def loadRSAPrivateKey(self, encryptor_name: str, private_path: str) -> RSA:
            """
            从指定路径加载 RSA 私钥，并返回 RSA 对象。

            参数：
                :param - encryptor_name: 加密器的名称，必须是字符串类型。
                :param - private_path: RSA 私钥的文件路径。

            返回：
                :return - RSA: 返回加载的 RSA 私钥对象，如果加载失败或加密器无效，则返回 None。

            执行过程：
                1. 检查 `encryptor_name` 是否为字符串，若无效则记录错误并返回 None。
                2. 从加密器字典中获取指定名称的加密器实例。
                3. 如果找到加密器且其具有 `loadRSAPrivateKey` 方法，使用该方法从指定路径加载 RSA 私钥。
                4. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效、路径无效或加载私钥失败，记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"Load RSA private key parameter error : encryptor name must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "loadRSAPrivateKey"):
                return encryptor.loadRSAPrivateKey(private_path)
            else:
                return None

        def loadRSAPublicKey(self, encryptor_name: str, public_path) -> RSA:
            """
            从指定路径加载 RSA 公钥，并返回 RSA 对象。

            参数：
                :param - encryptor_name: 加密器的名称，必须是字符串类型。
                :param - public_path: RSA 公钥的文件路径。

            返回：
                :return - RSA: 返回加载的 RSA 公钥对象，如果加载失败或加密器无效，则返回 None。

            执行过程：
                1. 检查 `encryptor_name` 是否为字符串，若无效则记录错误并返回 None。
                2. 从加密器字典中获取指定名称的加密器实例。
                3. 如果找到加密器且其具有 `loadRSAPublicKey` 方法，使用该方法从指定路径加载 RSA 公钥。
                4. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效、路径无效或加载公钥失败，记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"Load RSA public key parameter error : encryptor name must be a string.")
                return
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "loadRSAPublicKey"):
                return encryptor.loadRSAPublicKey(public_path)
            else:
                return

        def rsaEncrypt(self, encryptor_name: str, public_key: bytes, data: str) -> bytes | None:
            """
            使用指定的加密器和公钥对数据进行 RSA 加密。

            参数：
                :param - encryptor_name: 加密器的名称，必须是字符串类型。
                :param - public_key: RSA 公钥，以字节形式提供。
                :param - data: 要加密的数据，必须是字符串类型。

            返回：
                :return - bytes: 返回加密后的数据，以字节形式。如果加密器名称无效或加密器不具备 `rsaEncrypt` 方法，则返回 None。

            执行过程：
                1. 检查 `encryptor_name` 是否为字符串，若无效则记录错误并返回 None。
                2. 从加密器字典中获取指定名称的加密器实例。
                3. 如果找到加密器且其具有 `rsaEncrypt` 方法，使用该方法对数据进行 RSA 加密。
                4. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效或加密器不具备 `rsaEncrypt` 方法，则记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"RSA encrypt parameter error : encryptor name must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "rsaEncrypt"):
                return encryptor.rsaEncrypt(public_key, data)
            else:
                return None

        def rsaDecrypt(self, encryptor_name: str, private_key: bytes, encrypted_data: bytes) -> str | None:
            """
            使用指定的加密器和私钥对加密数据进行 RSA 解密。

            参数：
                :param - encryptor_name: 加密器的名称，必须是字符串类型。
                :param - private_key: RSA 私钥，以字节形式提供。
                :param - encrypted_data: 加密后的数据，以字节形式提供。

            返回：
                :return - str: 返回解密后的数据。如果加密器名称无效或加密器不具备 `rsaDecrypt` 方法，则返回 None。

            执行过程：
                1. 检查 `encryptor_name` 是否为字符串，若无效则记录错误并返回 None。
                2. 从加密器字典中获取指定名称的加密器实例。
                3. 如果找到加密器且其具有 `rsaDecrypt` 方法，使用该方法对加密数据进行 RSA 解密。
                4. 如果加密器不存在或无效，返回 None。

            异常：
                1. 无显式异常处理，若加密器名称无效或加密器不具备 `rsaDecrypt` 方法，则记录错误并返回 None。
            """

            if not isinstance(encryptor_name, str):
                self._Logger.error(f"RSA decrypt parameter error : encryptor name must be a string.")
                return None
            encryptor: Encryptor = self.getEncryptor(encryptor_name)
            if encryptor and hasattr(encryptor, "rsaDecrypt"):
                return encryptor.rsaDecrypt(private_key, encrypted_data)
            else:
                return None
