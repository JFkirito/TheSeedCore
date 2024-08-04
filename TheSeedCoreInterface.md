# TheSeedInterface

## LoggerModule

### 日志记录器模块

- **`TheSeedCoreLogger`为单例模式，实例时如果传入的`LoggerName`已存在，则返回已存在的实例，否则创建新实例。**

### `TheSeedCoreLogger` - 基类

- **通过直接实例 `TheSeedCoreLogger` 类来创建日志记录器**
- **参数**：
    - `LoggerName`（必要）`str`：日志记录器名称。
    - `LoggerPath`（必要）`str`：日志文件路径，可以用 `TheSeed.LogsPath`。
    - `BackupCount`（可选）`int`：日志备份数量，默认为 `30`。
    - `Level`（可选）`Union[logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET]`：日志记录器级别，默认为 `logging.DEBUG`。
    - `Debug`（可选）`bool`：是否开启调试模式，默认为 False。

  ```
  from TheSeedCore import TheSeedCoreLogger
  custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  ```

### `setDebugMode` - 全局方法

- **设置日志记录器的调试模式**。
- **参数**：
    - `LoggerName`（必要）`str`：日志记录器名称。
    - `Debug`（必要）`bool`：是否开启调试模式。

  ```
  from TheSeedCore import setDebugMode
  setDebugMode(True)
  ```

### `setAllDebugMode` - 全局方法

- **设置所有日志记录器的调试模式**。
- **参数**：
    - `Debug`（必要）`bool`：是否开启调试模式。
  ```
  from TheSeedCore import setAllDebugMode
  setAllDebugMode(True)
  ```

## EncryptorModule

- **可以通过下面两种方式来创建加密器，`EncryptorManager` 为单例模式，在TheSeedCore启动时会自动创建实例, 因此您可以在任何地方直接调用`TheSeed`.`EncryptorManager`使用加密器管理器。**

- **加解密时请确保使用相同的加密器实例，否则无法解密数据。**

### 1.直接创建

- **通过直接实例 `TheSeedEncryptor` 类来创建加密器，需要手动管理实例的生命周期**


- **通过直接实例的方式创建的加密器如果第一个实例的`KeyringIdentifier`和第二个实例的`KeyringIdentifier`相同，则第二个实例的`AESName`会覆盖第一个实例的`AESName`**
    - **参数**：
        - `AESName`（必要） `str` ：AES 密钥名称。
        - `Logger`（必要） `TheSeedCoreLogger` ：日志记录器实例。
        - `KeyringIdentifier`（可选）`str`：Keyring的唯一标识符，不指定则使用 `AESName` + `设备编号` + `设备信息` 作为标识符。
   ```
   from TheSeedCore import * 
   custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
   custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
   ```

### 2.集中管理

- **通过`TheSeed`.`EncryptorManager`.`createEncryptor`方法创建加密器，加密器会被集中管理**


- **通过上述方法创建的加密器，日志记录器会统一使用实例`EncryptorManager`时传入的日志记录器**
    - **参数**
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `aes_name`（必要）`str` ：AES 密钥名称。
        - `keyring_identifier`（可选）`str` ：Keyring的唯一标识符，不指定则使用 `encryptor_name` + `设备编号` + `设备信息` 作为标识符。
   ```
   TheSeed.EncryptorManager.createEncryptor("custom_encryptor", "AsunaAES", "AsunaAESKey")
   ```

### `TheSeedEncryptor` - 基类

- **`aesEncrypt`** - AES加密数据
    - **参数**：
        - `data`（必要）`str`：要加密的字符串数据。
    - **返回**：
        - `str`：加密后的 Base64 编码字符串数据。

  ```
  from TheSeedCore import * 
  
  custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
  custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
  
  raw_data = "This is TheSeedCore AES encrypt demo"
  
  print(f"raw data：{raw_data}")
  
  encrypted_data = custom_encryptor.aesEncrypt(raw_data)
  
  print(f"encrypted data：{encrypted_data}")
  ```

- **`aesDecrypt`** - AES解密数据
    - **参数**：
        - `encrypted_data`（必要）`str`：加密的 Base64 编码数据。
    - **返回**：
        - `str`：解密后的字符串数据。

  ```
  from TheSeedCore import * 
  
  custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
  custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
  
  raw_data = "This is TheSeedCore AES encrypt demo"
  
  print(f"raw data：{raw_data}")
  
  encrypted_data = custom_encryptor.aesEncrypt(raw_data)
  
  print(f"encrypted data：{encrypted_data}")
  
  decrypted_data = custom_encryptor.aesDecrypt(encrypted_data)
  
  print(f"decrypted data：{decrypted_data}")
  ```

- **`generateRSAKeys`** - 生成RSA密钥对
    - **如果提供的密钥长度无效，将使用默认的 2048 位。**
    - **如果指定了 `store_locally` 但是没有指定 `private_path` 或 `public_path`，则会返回 `None` 。**
    - **在指定了 `store_locally`，`private_path`，`public_path` 参数的情况下，会将私钥和公钥存储到指定的路径，私钥会使用该加密器实例的 `aesEncrypt` 进行AES加密。**
    - **无论是否存储本地，都将返回一组未加密的私钥和公钥。**
    - **参数**：
        - `private_path`（可选）`bool`：私钥存储路径。
        - `public_path`（可选）`str`：公钥存储路径。
        - `key_size`（可选）`int`：密钥长度，默认为 `2048`，只接受`1024`, `2048`, `3072`, `4096`。
        - `store_locally`（可选）`str`：是否将私钥存储到本地，默认为 False。
    - **返回**：
        - `tuple[bytes, bytes] `：私钥和公钥。

    ```
    from TheSeedCore import * 
  
    custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
    custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
  
    private_key, public_key = custom_encryptor.generateRSAKeys()
  
    print(f"public key：{public_key}")
  
    print(f"private key：{private_key}")
    ```

- **`loadRSAPrivateKey`** - 从文件中加载RSA私钥
    - **如果提供的密钥无效，将返回 `None`。**
    - **参数**：
        - `private_path`（必要）`str`：私钥路径。
    - **返回**：
        - `RSA`：RSA私钥对象。

    ```
    from TheSeedCore import * 
  
    custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
    custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
    
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = custom_encryptor.generateRSAKeys(private_key_save_path, public_key_save_path, 2048, True)
 
    loaded_private_key = custom_encryptor.loadRSAPrivateKey(private_key_save_path)
  
    print(f"loaded private key：{loaded_private_key}")
    ```

- **`loadRSAPublicKey`** - 从文件中加载RSA公钥
    - **如果提供的密钥无效，将返回 `None`。**
    - **参数**：
        - `public_path`（必要）`str`：公钥路径。
    - **返回**：
        - `RSA`：RSA公钥对象。

    ```
    from TheSeedCore import * 
  
    custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
    custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
    
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = custom_encryptor.generateRSAKeys(private_key_save_path, public_key_save_path, 2048, True)
 
    loaded_public_key = custom_encryptor.loadRSAPublicKey(public_key_save_path)
  
    print(f"loaded public key：{loaded_public_key}")
    ```

- **`rsaEncrypt`** - RSA加密数据
    - **参数**：
        - `public_key`（必要）`bytes`：RSA公钥的字节串。
        - `data`（必要）`str`：要加密的字符串数据。
    - **返回**：
        - `bytes`：加密后的字节数据。

    ```
    from TheSeedCore import * 
  
    custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
    custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
    
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = custom_encryptor.generateRSAKeys(private_key_save_path, public_key_save_path, 2048, True)
  
    raw_data = "This is TheSeedCore RSA encrypt demo"
  
    print(f"raw data：{raw_data}")
  
    encrypted_data = custom_encryptor.rsaEncrypt(raw_data, public_key)
  
    print(f"encrypted data：{encrypted_data}")
    ```

- **`rsaDecrypt`** - RSA解密数据
    - **参数**：
        - `private_key`（必要）`bytes`：RSA私钥的字节串。
        - `encrypted_data`（必要）`bytes`：加密的字节数据。
    - **返回**：
        - `str`：解密后的字符串数据。

    ```
    from TheSeedCore import * 
  
    custom_logger = TheSeedCoreLogger("customLogger", TheSeed.LogsPath, 30, logging.INFO, False)
  
    custom_encryptor = TheSeedEncryptor("AsunaAES", custom_logger, "AsunaAESKey")
    
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = custom_encryptor.generateRSAKeys(private_key_save_path, public_key_save_path, 2048, True)
  
    raw_data = "This is TheSeedCore RSA encrypt demo"
  
    print(f"raw data：{raw_data}")
  
    encrypted_data = custom_encryptor.rsaEncrypt(raw_data, public_key)
  
    print(f"encrypted data：{encrypted_data}")
  
    decrypted_data = custom_encryptor.rsaDecrypt(encrypted_data, private_key)
  
    print(f"decrypted data：{decrypted_data}")
    ```

### `EncryptorManager` - 加密器管理器

- **`createEncryptor`** - 创建加密器
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `aes_name`（必要）`str` ：AES 密钥名称。
        - `keyring_identifier`（可选）`str` ：Keyring的唯一标识符，不指定则使用 `encryptor_name` + `设备编号` + `设备信息` 作为标识符。

    ```
    from TheSeedCore import * 
  
    TheSeed.EncryptorManager.createEncryptor("custom_encryptor", "AsunaAES", "AsunaAESKey")
    ```

- **`getEncryptor`** - 获取加密器
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
    - **返回**：
        - `TheSeedEncryptor`：加密器实例。

    ```
    from TheSeedCore import * 
  
    custom_encryptor = TheSeed.EncryptorManager.getEncryptor("custom_encryptor")
    ```

- **`aesEncryptData`** - AES加密数据
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `data`（必要）`str`：要加密的字符串数据。
    - **返回**：
        - `str`：加密后的 Base64 编码字符串数据。

    ```
    from TheSeedCore import * 
    
    raw_data = "This is TheSeedCore AES encrypt demo"
    
    print(raw_data)
  
    encrypted_data = TheSeed.EncryptorManager.aesEncryptData("custom_encryptor", raw_data)
  
    print(encrypted_data)
    ```

- **`aesDecryptData`** - AES解密数据
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `encrypted_data`（必要）`str`：加密的 Base64 编码数据。
    - **返回**：
        - `str`：解密后的字符串数据。

    ```
    from TheSeedCore import * 
    
    raw_data = "This is TheSeedCore AES encrypt demo"
    
    print(raw_data)
  
    encrypted_data = TheSeed.EncryptorManager.aesEncryptData("custom_encryptor", raw_data)
  
    print(encrypted_data)
  
    decrypted_data = TheSeed.EncryptorManager.aesDecryptData("custom_encryptor", encrypted_data)
  
    print(decrypted_data)
    ```

- **`generateRSAKeys`** - 生成RSA密钥对
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `private_path`（可选）`str`：私钥存储路径。
        - `public_path`（可选）`str`：公钥存储路径。
        - `key_size`（可选）`int`：密钥长度，默认为 `2048`，只接受`1024`, `2048`, `3072`, `4096`。
        - `store_locally`（可选）`str`：是否将私钥存储到本地，默认为 False。
    - **返回**：
        - `tuple[bytes, bytes] `：私钥和公钥。

    ```
    from TheSeedCore import * 
  
    private_key, public_key = TheSeed.EncryptorManager.generateRSAKeys("custom_encryptor")
  
    print(f"public key：{public_key}")
  
    print(f"private key：{private_key}")
    ```

- **`loadRSAPrivateKey`** - 从文件中加载RSA私钥
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `private_path`（必要）`str`：私钥路径。
    - **返回**：
        - `RSA`：RSA私钥对象。

    ```
    from TheSeedCore import * 
  
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = TheSeed.EncryptorManager.generateRSAKeys("custom_encryptor", private_key_save_path, public_key_save_path, 2048, True)
 
    loaded_private_key = TheSeed.EncryptorManager.loadRSAPrivateKey("custom_encryptor", private_key_save_path)
  
    print(f"loaded private key：{loaded_private_key}")
    ```

- **`loadRSAPublicKey`** - 从文件中加载RSA公钥
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `public_path`（必要）`str`：公钥路径。
    - **返回**：
        - `RSA`：RSA公钥对象。

    ```
    from TheSeedCore import * 
  
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = TheSeed.EncryptorManager.generateRSAKeys("custom_encryptor", private_key_save_path, public_key_save_path, 2048, True)
 
    loaded_public_key = TheSeed.EncryptorManager.loadRSAPublicKey("custom_encryptor", public_key_save_path)
  
    print(f"loaded public key：{loaded_public_key}")
    ```

- **`rsaEncrypt`** - RSA加密数据
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `public_key`（必要）`bytes`：RSA公钥的字节串。
        - `data`（必要）`str`：要加密的字符串数据。
    - **返回**：
        - `bytes`：加密后的字节数据。

    ```
    from TheSeedCore import * 
  
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = TheSeed.EncryptorManager.generateRSAKeys("custom_encryptor", private_key_save_path, public_key_save_path, 2048, True)
  
    raw_data = "This is TheSeedCore RSA encrypt demo"
  
    print(f"raw data：{raw_data}")
  
    encrypted_data = TheSeed.EncryptorManager.rsaEncrypt("custom_encryptor", raw_data, public_key)
  
    print(f"encrypted data：{encrypted_data}")
    ```

- **`rsaDecrypt`** - RSA解密数据
    - **参数**：
        - `encryptor_name`（必要）`str` ：加密器ID。
        - `private_key`（必要）`bytes`：RSA私钥的字节串。
        - `encrypted_data`（必要）`bytes`：加密的字节数据。
    - **返回**：
        - `str`：解密后的字符串数据。

    ```
    from TheSeedCore import * 
  
    private_key_save_path = "private.pem"
    
    public_key_save_path = "public.pem"
  
    private_key, public_key = TheSeed.EncryptorManager.generateRSAKeys("custom_encryptor", private_key_save_path, public_key_save_path, 2048, True)
  
    raw_data = "This is TheSeedCore RSA encrypt demo"
  
    print(f"raw data：{raw_data}")
  
    encrypted_data = TheSeed.EncryptorManager.rsaEncrypt("custom_encryptor", raw_data, public_key)
  
    print(f"encrypted data：{encrypted_data}")
  
    decrypted_data = TheSeed.EncryptorManager.rsaDecrypt("custom_encryptor", encrypted_data, private_key)
  
    print(f"decrypted data：{decrypted_data}")
    ```

## DatabaseModule

- **SQLite数据库具有单一写锁的特性，所以单个数据库在进行写操作时请在同一线程中完成**


- **Redis数据库的接口请参阅源码的注释-.-b**

### `_BasicSQLiteDatabase` - SQLite数据库基类

- **在 `DatabaseModule` 模块中继承此类可以实现自定义的SQLite数据库，具体可以参考 `DatabaseModule` 模块的 `_CustomSQLiteDatabase` 类设计**

### `_BasicRedisDatabase` - Redis数据库基类

- **在 `DatabaseModule` 模块中继承此类可以实现自定义的Redis数据库**

### `_CustomSQLiteDatabase` - 自定义SQLite数据库

- **此类继承自`_BasicSQLiteDatabase`，可以参考此类的设计拓展出自定义的SQLite数据库**

### `TheSeedDatabaseManager` - TheSeedCore 的数据库管理器

- **此管理器在TheSeedCore启动时会自动创建实例，您可以在任何地方直接调用 `TheSeed`.`BasicDatabaseManager` 使用TheSeedCore的数据库管理器**


- **在使用 `TheSeed`.`BasicDatabaseManager` 时，请注意尽量不要对以下属性进行操作，否则可能会影响 TheSeedCore 的运行**
    - `FirstRun`：是否第一次运行，默认为0，设置为1时 TheSeedCore 的下次启动将不会初始化配置数据，而是使用上一次启动时的配置数据。
    - `StartTime`：TheSeedCore 的启动时间。
    - `CloseTime`：TheSeedCore 的关闭时间。
    - `PerformanceMode`：线程池的性能模式。
    - `TaskThreshold`：线程池的任务阈值。
    - `TheSeedHost`：TheSeedCore 的主机地址。
    - `TheSeedHttpPort`：TheSeedCore 的HTTP服务端口号。
    - `TheSeedWsPort`：TheSeedCore 的WebSocket服务端口号。

- **`upsertItem`** - 插入或更新数据
    - **参数**：
        - `item_id`（必要）`str`：数据唯一标识。
        - `item_value`（必要）`str`：数据值。
        - `encrypt`（可选）`bool`：是否加密，默认为 False。
        - `encrypt_column`（可选）`list`：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.BasicDatabaseManager.upsertItem("user", "Asuna", True, ["ItemValue"])
    ```

- **`upsertItems`** - 批量插入或更新数据
    - **参数**：
        - `items_data`（必要）`list`：数据字典。
        - `encrypt`（可选）`bool`：是否加密，默认为 False。
        - `encrypt_column`（可选）`list`：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    items = [
        {ItemID: "user", ItemValue: "Asuna"},
        {ItemID: "password, ItemValue: "123456"}
    ]
  
    TheSeed.BasicDatabaseManager.upsertItems(items, True, ["ItemValue"])
    ```

- **`updateItem`** - 更新数据
    - **参数**：
        - `item_id`（必要）`str`：数据唯一标识。
        - `item_value`（必要）`str`：数据值。
        - `encrypt`（可选）`bool`：是否加密，默认为 False。
        - `encrypt_column`（可选）`list`：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.BasicDatabaseManager.updateItem("user", "Asuna")
    ```

- **`searchItem`** - 查询数据
    - **参数**：
        - `item_id`（必要）`str`：数据唯一标识。
        - `decrypt`（可选）`bool`：是否解密，默认为 False。
        - `decrypt_column`（可选）`list`：需要解密的数据列列表。
    - **返回**：
        - `str`：数据值。

    ```
    from TheSeedCore import *
  
    item_value = TheSeed.BasicDatabaseManager.searchItem("user", True, ["ItemValue"])
    ```

- **`searchItems`** - 批量查询数据
    - **参数**：
        - `order_by_column`（必要）`str`| `None`：排序列的名称，可选。
        - `decrypt`（可选）`bool`：是否解密，默认为 False。
        - `decrypt_column`（可选）`list`：需要解密的数据列列表。
    - **返回**：
        - `list`：数据字典。

    ```
    from TheSeedCore import *
  
    item_values = TheSeed.BasicDatabaseManager.searchItems(None, True, ["ItemValue"])
    ```

- **`deleteItem`** - 删除数据
    - **参数**：
        - `item_id`（必要）`str`：数据唯一标识。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.BasicDatabaseManager.deleteItem("user")
    ```

- **`deleteAllItems`** - 删除所有数据
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.BasicDatabaseManager.deleteAllItems()
    ```

- **`closeDatabase`** - 关闭数据库
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.BasicDatabaseManager.closeDatabase()
    ```

### `SQLiteDatabaseManager` - SQLite数据库管理器

- **`createSQLiteDatabase`** - 创建SQLite数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `tables_structured`（必要）`dict` ：数据库表结构定义，包括表名和列信息。
        - `stay_connected`（可选）`bool` ：是否保持连接，默认为 False。
        - `database_path`（可选）`str` ：数据库路径，默认为 `TheSeed.DatabasePath`。
        - `logger`（可选）`TheSeedCoreLogger` ：日志记录器，默认为`TheSeed.BasicSQLiteDatabaseLogger`。
        - `encryptor`（可选）`TheSeedEncryptor` ：加密器，默认为`TheSeed.BasicEncryptor`。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
    custom_database_tables = {
            "Yui": {
                "primary_key": ("ItemID", "TEXT PRIMARY KEY"),
                "columns": {
                    "ItemValue": "TEXT NOT NULL",
                }
            },
            "Asuna": {
                "primary_key": ("ItemID", "TEXT PRIMARY KEY"),
                "columns": {
                    "ItemValue": "TEXT NOT NULL",
                }
            }
        }
    TheSeed.SQLiteDatabaseManager.createSQLiteDatabase("custom_database", custom_database_tables, True)
    ```

- **`getDatabase`** - 获取数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
    - **返回**：
        - `_CustomSQLiteDatabase`：数据库实例。

    ```
    from TheSeedCore import *
  
    custom_database = TheSeed.SQLiteDatabaseManager.getDatabase("custom_database")
    ```

- **`getExistingTables`** - 获取数据库中已存在的表
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
    - **返回**：
        - `list`：表名列表。

    ```
    from TheSeedCore import *
  
    existing_tables = TheSeed.SQLiteDatabaseManager.getExistingTables("custom_database")
    ```

- **`checkExistingTables`** - 检查数据库中是否存在指定的表
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
    - **返回**：
        - `bool`：是否存在。

    ```
    from TheSeedCore import *
  
    is_existing = TheSeed.SQLiteDatabaseManager.checkExistingTables("custom_database", "Yui")
    ```

- **`deleteTable`** - 删除数据库中的表
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.SQLiteDatabaseManager.deleteTable("custom_database", "Yui")
    ```

- **`upsertData`** - 插入或更新数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `update_data`（必要）`dict` ：数据字典。
        - `encrypt`（可选）`bool` ：是否加密，默认为 False。
        - `encrypt_column`（可选）`list` ：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    data = {
        "ItemID": "user",
        "ItemValue": "Asuna"
    }
  
    TheSeed.SQLiteDatabaseManager.upsertData("custom_database", "Yui", data, True, ["ItemValue"])
    ```

- **`upsertDatas`** - 批量插入或更新数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `update_datas`（必要）`list` ：数据字典列表。
        - `encrypt`（可选）`bool` ：是否加密，默认为 False。
        - `encrypt_column`（可选）`list` ：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    datas = [
        {
            "ItemID": "user",
            "ItemValue": "Asuna"
        },
        {
            "ItemID": "password",
            "ItemValue": "123456"
        }
    ]
  
    TheSeed.SQLiteDatabaseManager.upsertDatas("custom_database", "Yui", datas, True, ["ItemValue"])
    ```

- **`updateData`** - 更新数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `update_data`（必要）`dict` ：数据字典。
        - `where_clause`（必要）`str` ：条件子句。
        - `where_args`（必要）`list` ：条件参数。
        - `encrypt`（可选）`bool` ：是否加密，默认为 False。
        - `encrypt_column`（可选）`list` ：需要加密的数据列列表。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    data = {
        "ItemID": "user",
        "ItemValue": "Asuna"
    }
  
    TheSeed.SQLiteDatabaseManager.updateData("custom_database", "Yui", data, "ItemID = ?", ["user"], True, ["ItemValue"])
    ```

- **`searchData`** - 查询数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `unique_id`（必要）`str` ：要查找的数据。
        - `unique_id_column`（必要）`str` ：要查找的数据的列名。
        - `decrypt`（可选）`bool` ：是否解密，默认为 False。
        - `decrypt_column`（可选）`list` ：需要解密的数据列列表。
    - **返回**：
        - `list`：数据字典。

    ```
    from TheSeedCore import *

    data = TheSeed.SQLiteDatabaseManager.searchData("custom_database", "Yui", "user", "ItemID", True, ["ItemValue"])
    ```

- **`searchDatas`** - 批量查询数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `sort_by_column`（可选）`str`| `None`：按指定列排序。
        - `decrypt`（可选）`bool` ：是否解密，认为 False。
        - `decrypt_column`（可选）`list` ：需要解密的数据列列表。
    - **返回**：
        - `list`：多条数据记录列表。

    ```
    from TheSeedCore import *
  
    datas = TheSeed.SQLiteDatabaseManager.searchDatas("custom_database", "Yui", None, True, ["ItemValue"])
    ```

- **`deleteData`** - 删除数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `where_clause`（必要）`str` ：条件子句。
        - `where_args`（必要）`list` ：条件参数。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.SQLiteDatabaseManager.deleteData("custom_database", "Yui", "ItemID = ?", ["user"])
    ```

- **`deleteDatas`** - 删除多条数据
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `table_name`（必要）`str` ：表名。
        - `where_clause`（可选）`str` ：条件子句, 不指定则删除表中所有数据。
        - `where_args`（可选）`list` ：条件参数。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.SQLiteDatabaseManager.deleteAllDatas("custom_database", "Yui")
    ```

- **`closeDatabase`** - 关闭数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.SQLiteDatabaseManager.closeDatabase("custom_database")
    ```

- **`closeAllDatabase`** - 关闭所有数据库
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.SQLiteDatabaseManager.closeAllDatabase()
    ```

### `RedisDatabaseManager` - Redis数据库管理器

- **`createRedisDatabase`** - 创建Redis数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
        - `host`（必要）`str` ：数据库主机地址。
        - `port`（必要）`int` ：数据库端口号。
        - `password`（可选）`str` ：数据库密码，默认为 None。
        - `db`（可选）`int` ：数据库编号，默认为 0。
        - `logger`（可选）`TheSeedCoreLogger` ：日志记录器，默认为`TheSeed.BasicRedisDatabaseLogger`。
        - `encryptor`（可选）`TheSeedEncryptor` ：加密器，默认为`TheSeed.BasicEncryptor`。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.RedisDatabaseManager.createRedisDatabase("custom_redis_database", "localhost", 6379)
    ```

- **`getRedisDatabase`** - 获取数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
    - **返回**：
        - `_CustomRedisDatabase`：数据库实例。

    ```
    from TheSeedCore import *
  
    custom_database = TheSeed.RedisDatabaseManager.getRedisDatabase("custom_redis_database")
    ```

- **`closeRedisDatabase`** - 关闭数据库
    - **参数**：
        - `database_id`（必要）`str` ：数据库名称。
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.RedisDatabaseManager.closeRedisDatabase("custom_redis_database")
    ```

- **`closeAllDatabase`** - 关闭所有数据库
    - **返回**：
        - `bool`：是否成功。

    ```
    from TheSeedCore import *
  
    TheSeed.RedisDatabaseManager.closeAllDatabase()
    ```

## NetworkModule

### `HTTPServer` - HTTP服务器

- **在TheSeedCore启动时会自动创建一个默认的HTTP服务器，但不会启动，您可以在任何地方直接调用 `TheSeed`.`HttpServer` 使用默认的HTTP服务器**


- **如果需要自定义HTTP服务器或者需要多个HTTP服务器实例，可以继承调用或者直接实例该类**

- **`checkRoute`** - 检查路由
    - **参数**：
        - `method`（必要）`str` ：请求方法。
        - `path`（必要）`str` ：路由路径。
    - **返回**：
        - `bool`：是否存在。

    ```
    from TheSeedCore import *
  
    is_existing = TheSeed.HttpServer.checkRoute("GET", "/")
    ```

- **`addRoute`** - 添加路由
    - **参数**：
        - `method`（必要）`str` ：请求方法。
        - `path`（必要）`str` ：路由路径。
        - `processor`（必要）`Callable[[Request], Any]` ：路由处理器。

    ```
    from TheSeedCore import *
    
    def route_processor(request: Request) -> Response:
        return Response(200, "This is TheSeedCore route processor")
    
    TheSeed.HttpServer.addRoute("GET", "/", route_processor)
    ```

- **`getHost`** - 获取主机地址
    - **返回**：
        - `str`：主机地址。

    ```
    from TheSeedCore import *
  
    host = TheSeed.HttpServer.getHost()
    ```

- **`getPort`** - 获取主机端口
    - **返回**：
        - `str`：主机端口。

    ```
    from TheSeedCore import *
  
    port = TheSeed.HttpServer.getPort()
    ```

- **`getServerAddress`** - 获取服务器地址
    - **返回**：
        - `str`：服务器地址。

    ```
    from TheSeedCore import *
  
    server_address = TheSeed.HttpServer.getServerAddress()
    ```

- **`setAddress`** - 设置服务器地址并重启服务
    - **参数**：
        - `host`（必要）`str` ：主机地址。
        - `port`（必要）`int` ：主机端口。

    ```
    from TheSeedCore import *
  
    TheSeed.addAsyncTask(TheSeed.HttpServer.setAddress, host="localhost", port="8080")
    ```

- **`startHTTPServer`** - 启动HTTP服务器
    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.HttpServer.startHTTPServer)
    ```
- **`stopHTTPServer`** - 停止HTTP服务器
    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.HttpServer.stopHTTPServer)
    ```

### `WebSocketServer` - WebSocket服务器

- **在TheSeedCore启动时会自动创建一个默认的WebSocket服务器，但不会启动，您可以在任何地方直接调用 `TheSeed`.`WebSocketServer` 使用默认的WebSocket服务器**


- **如果需要自定义WebSocket服务器或者需要多个WebSocket服务器实例，可以继承调用或者直接实例该类**


- **`setMsgProcessor`** - 设置消息处理器
    - **参数**：
        - `processor`（必要）`Callable[..., Coroutine[Any, Any, Any]]` ：消息处理器，必须是异步方法。

    ```
    from TheSeedCore import *
    
    async def msg_processor(ws: WebSocket, msg: str) -> None:
        ws.send("This is TheSeedCore msg processor")
    
    TheSeed.WebSocketServer.setMsgProcessor(msg_processor)
    ```

- **`setWsProcessor`** - 设置WebSocket处理器
    - **参数**：
        - `processor`（必要）`Callable[..., Coroutine[Any, Any, Any]]` ：WebSocket处理器，必须是异步方法。

    ```
    from TheSeedCore import *
    
    async def ws_processor(ws: WebSocket, path) -> None:
        ws.send("This is TheSeedCore ws processor")
    
    TheSeed.WebSocketServer.setWsProcessor(ws_processor)
    ```

- **`getHost`** - 获取主机地址
    - **返回**：
        - `str`：主机地址。

    ```
    from TheSeedCore import *
  
    host = TheSeed.WebSocketServer.getHost()
    ```

- **`getPort`** - 获取主机端口
    - **返回**：
        - `str`：主机端口。

    ```
    from TheSeedCore import *
  
    port = TheSeed.WebSocketServer.getPort()
    ```

- **`getServerAddress`** - 获取服务器地址
    - **返回**：
        - `str`：服务器地址。

    ```
    from TheSeedCore import *
  
    server_address = TheSeed.WebSocketServer.getServerAddress()
    ```

- **`getAllClients`** - 获取所有客户端
    - **返回**：
        - `dict`：客户端字典。

    ```
    from TheSeedCore import *
  
    clients = TheSeed.WebSocketServer.getAllClients()
    ```

- **`startWebSocketServer`** - 启动WebSocket服务器
    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.WebSocketServer.startWebSocketServer)
    ```

- **`stopWebSocketServer`** - 停止WebSocket服务器
    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.WebSocketServer.stopWebSocketServer)
    ```

- **`sendMsg`** - 发送消息
    - **参数**：
        - `client_id`（必要）`str` ：客户端ID。
        - `message`（必要）`Any` ：消息内容。

    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.WebSocketServer.sendMsg, client_id="client_id", message="This is TheSeedCore msg")
    ```

- **`broadcast`** - 广播消息
    - **参数**：
        - `message`（必要）`Any` ：消息内容。

    ```
    from TheSeedCore import *
    
    TheSeed.addAsyncTask(TheSeed.WebSocketServer.broadcast, message="This is TheSeedCore msg")
    ```

### `WebSocketClient` - WebSocket客户端

- **如果需要自定义WebSocket客户端或者需要多个WebSocket客户端实例，可以继承调用或者直接实例该类**

- **具体调用请参阅源码的注释-.-b**

## ExternalServicesModule

### 外部服务模块

- **目前只支持NodeJS的调用，TheSeedCore启动时会创建一个默认的`NodeService`**


- **`NodeService`类设计为单例模式，您可以在任何地方调用`TheSeed`.`NodeService`来管理您的NodeJS服务**

### `NodeService` - NodeJS服务

- **`installPackage`** - 安装NodeJS包
    - **参数**：
        - `package_name`（必要）`str` ：包名。
        - `package_version`（可选）`str` ：包版本，默认为 latest。
        - `install_path`（可选）`str` ：安装路径，默认为 `TheSeed.ExternalServicePath`。
        - `basic_logger`（可选）`TheSeedCoreLogger` ：日志记录器，默认为`TheSeed.BasicExternalServicesLogger`。

    ```
    from TheSeedCore import *
  
    TheSeed.addSyncTask(TheSeed.NodeService.installPackage, package_name="<package_name>")
    ```

- **`startService`** - 启动NodeJS服务
    - **参数**：
        - `package_name`（必要）`str` ：包名。
        - `application`（必要）`str` ：应用程序路径。
        - `application_path`（可选）`str` ：应用程序路径，未指定则使用 `TheSeed.ExternalServicePath` 。
        - `node_path`（可选）`str` ：Node.js的执行路径, 未指定则使用系统环境变量中的路径。
        - `basic_logger`（可选）`TheSeedCoreLogger` ：日志记录器，默认为`TheSeed.BasicExternalServicesLogger`。

    ```
    from TheSeedCore import *
  
    TheSeed.addSyncTask(TheSeed.NodeService.startService, package_name="<service_name>", application="<application>")
    ```


- **`stopService`** - 停止NodeJS服务
    - **参数**：
        - `package_name`（必要）`str` ：包名。
        - `basic_logger`（可选）`TheSeedCoreLogger` ：日志记录器，默认为`TheSeed.BasicExternalServicesLogger`。

    ```
    from TheSeedCore import *
  
    TheSeed.addSyncTask(TheSeed.NodeService.stopService, package_name="<service_name>")
    ```

- **`stopAllNodeService`** - 停止所有NodeJS服务
    ```
    from TheSeedCore import *
  
    TheSeed.addSyncTask(TheSeed.NodeService.stopAllNodeService)
    ```


