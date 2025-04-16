# PostgreSQL-MCP

PostgreSQL-MCP 是一个基于 MCP 框架的 PostgreSQL 数据库接口服务，提供了简单易用的 PostgreSQL 数据库操作工具。

## 安装

1. 克隆本仓库
2. 创建虚拟环境并安装依赖

```bash
cd postgresql-mcp
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
pip install -e .
```

## 使用方法

通过环境变量或命令行参数配置数据库连接：

```bash
# 通过环境变量
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DATABASE=postgres

# 启动服务
python postgresql-mcp.py
```

或使用命令行参数：

```bash
python postgresql-mcp.py --host localhost --port 5432 --user postgres --password postgres --database postgres
```

## 主要功能

- `execute_query`: 执行 SQL 查询
- `list_tables`: 列出指定模式中的所有表
- `describe_table`: 获取表结构
- `list_schemas`: 列出数据库中的所有模式

## 注意事项

确保 PostgreSQL 服务器已启动且可访问。 