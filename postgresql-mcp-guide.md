# PostgreSQL MCP 开发指南 🐘

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastMCP](https://img.shields.io/badge/FastMCP-0.1.0-blue?style=flat-square)](https://github.com/your-fastmcp-repo)

## 简介 🚀

PostgreSQL MCP 是一个基于 FastMCP 框架的 PostgreSQL 数据库交互服务。它提供了一套简单易用的工具函数，让你能够通过 API 方式与 PostgreSQL 数据库进行交互。

## 功能特点 ✨

- 🔄 数据库连接管理与重试机制
- 🔍 执行 SQL 查询并获取结果
- 📋 数据库元数据操作（列出表、模式等）
- 📝 表结构管理（创建表、描述表结构）
- 💾 数据操作（插入、更新数据）

## 快速开始 🏃‍♂️

### 配置选项

PostgreSQL MCP 支持通过环境变量或命令行参数进行配置：

| 配置项 | 环境变量 | 默认值 |
|-------|---------|-------|
| 主机地址 | `POSTGRES_HOST` | localhost |
| 端口 | `POSTGRES_PORT` | 5432 |
| 用户名 | `POSTGRES_USER` | postgres |
| 密码 | `POSTGRES_PASSWORD` | postgres |
| 数据库 | `POSTGRES_DATABASE` | postgres |
| 连接超时 | `POSTGRES_CONNECTION_TIMEOUT` | 10 |
| 重试次数 | `POSTGRES_CONNECT_RETRY_COUNT` | 3 |

### 运行服务

```bash
python postgresql-mcp.py --host localhost --port 5432 --user postgres --password yourpassword --database yourdb
```

## API 功能 📚

### 执行 SQL 查询 

```python
response = await execute_query(
    query="SELECT * FROM users WHERE age > %s",
    params=[18],
    db_config={"database": "custom_db"}
)
```

### 列出数据库中的表

```python
tables = await list_tables(schema_name="public")
```

### 获取表结构

```python
table_info = await describe_table(
    table_name="users",
    schema_name="public"
)
```

### 列出所有模式

```python
schemas = await list_schemas()
```

### 创建新表

```python
result = await create_table(
    table_name="new_table",
    columns=[
        {"name": "id", "type": "SERIAL", "primary_key": True},
        {"name": "name", "type": "VARCHAR(100)", "nullable": False},
        {"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}
    ]
)
```

### 插入数据

```python
result = await insert_data(
    table_name="users",
    data=[
        {"name": "张三", "age": 30, "email": "zhangsan@example.com"},
        {"name": "李四", "age": 25, "email": "lisi@example.com"}
    ]
)
```

### 更新数据

```python
result = await update_data(
    table_name="users",
    data={"status": "inactive", "updated_at": "CURRENT_TIMESTAMP"},
    condition="user_id = %s",
    params=[1001]
)
```

## 错误处理 🔧

服务会提供详细的错误信息，常见问题包括：

- 连接失败（主机/端口错误）
- 身份验证失败（用户名/密码错误）
- 数据库不存在
- SQL 语法错误
- 表或列不存在
- 违反表约束条件

## 实现细节 🔍

该服务基于以下关键技术：
- `psycopg2` 库用于 PostgreSQL 连接
- FastMCP 框架提供 API 接口
- 参数化查询防止 SQL 注入
- 自动重试机制提高可靠性

## 最佳实践 💡

- 始终使用参数化查询防止 SQL 注入
- 为所有更新操作提供 WHERE 条件
- 利用连接配置优化数据库性能
- 根据实际需求调整连接超时和重试次数

---

⚠️ **注意**：在生产环境中使用时，请确保设置安全的数据库密码，并适当限制数据库用户权限。 