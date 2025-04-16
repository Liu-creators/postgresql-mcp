from typing import Any, List, Dict, Optional, Union
import os
import argparse
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP server
mcp = FastMCP("postgresql")

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='PostgreSQL MCP服务')
    parser.add_argument('--host', type=str, help='数据库主机地址')
    parser.add_argument('--port', type=int, help='数据库端口')
    parser.add_argument('--user', type=str, help='数据库用户名')
    parser.add_argument('--password', type=str, help='数据库密码')
    parser.add_argument('--database', type=str, help='数据库名称')
    parser.add_argument('--connection-timeout', type=int, help='连接超时时间(秒)')
    parser.add_argument('--connect-retry-count', type=int, help='连接重试次数')
    return parser.parse_args()

# 数据库连接配置默认值
DEFAULT_DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "database": os.getenv("POSTGRES_DATABASE", "postgres"),
    "connect_timeout": int(os.getenv("POSTGRES_CONNECTION_TIMEOUT", "10")),  # 连接超时时间(秒)
    "connect_retry_count": int(os.getenv("POSTGRES_CONNECT_RETRY_COUNT", "3"))  # 连接重试次数
}

# 从命令行参数获取配置
def get_config_from_args():
    args = parse_args()
    cmd_config = {}
    
    if args.host:
        cmd_config["host"] = args.host
    if args.port:
        cmd_config["port"] = args.port
    if args.user:
        cmd_config["user"] = args.user
    if args.password:
        cmd_config["password"] = args.password
    if args.database:
        cmd_config["database"] = args.database
    if args.connection_timeout:
        cmd_config["connect_timeout"] = args.connection_timeout
    if args.connect_retry_count:
        cmd_config["connect_retry_count"] = args.connect_retry_count
    
    # 合并配置
    config = DEFAULT_DB_CONFIG.copy()
    config.update(cmd_config)
    
    return config

# 全局数据库配置
GLOBAL_DB_CONFIG = None

def get_connection(db_config=None):
    """获取数据库连接
    
    Args:
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        数据库连接对象
    """
    # 如果没有提供配置，先尝试使用全局配置，再使用默认配置
    if db_config is None:
        if GLOBAL_DB_CONFIG is not None:
            db_config = GLOBAL_DB_CONFIG.copy()
        else:
            db_config = DEFAULT_DB_CONFIG.copy()
    else:
        # 合并用户提供的配置和全局/默认配置
        if GLOBAL_DB_CONFIG is not None:
            config = GLOBAL_DB_CONFIG.copy()
        else:
            config = DEFAULT_DB_CONFIG.copy()
        config.update(db_config)
        db_config = config
    
    retry_count = 0
    last_error = None
    max_retries = db_config.pop("connect_retry_count", 3)
    
    while retry_count < max_retries:
        try:
            # 创建一个配置字典的副本
            conn_params = db_config.copy()
                
            conn = psycopg2.connect(**conn_params)
            return conn
        except Error as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                # 只有在还有重试机会的情况下打印重试信息
                print(f"第 {retry_count} 次连接失败，正在重试... 错误: {e}")
    
    # 所有重试都失败后，构建详细的错误信息
    error_message = f"数据库连接错误(重试 {retry_count} 次后): {last_error}"
    if "connection refused" in str(last_error).lower():
        error_message += f"\n无法连接到PostgreSQL服务器，请检查主机 {db_config['host']} 和端口 {db_config['port']} 是否正确"
        error_message += f"\n连接超时时间为 {db_config.get('connect_timeout', 10)} 秒"
    elif "password authentication failed" in str(last_error).lower():
        error_message += f"\n认证失败，请检查用户名 {db_config['user']} 和密码是否正确"
    elif "does not exist" in str(last_error).lower() and "database" in str(last_error).lower():
        error_message += f"\n未知数据库 {db_config['database']}，请确认数据库名称是否正确"
    raise Exception(error_message)

@mcp.tool()
async def execute_query(query: str, params: Optional[List[Any]] = None, db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """执行SQL查询语句，返回查询结果

    Args:
        query: SQL查询语句
        params: 查询参数，用于参数化查询，防止SQL注入
        db_config: 数据库连接配置参数，如果为None则使用默认配置

    Returns:
        包含查询结果的字典
    """
    if not query:
        return {"error": "查询语句不能为空"}
    
    if params is None:
        params = []
    
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        
        # 判断是否是需要返回结果集的查询
        query_upper = query.strip().upper()
        if query_upper.startswith("SELECT") or query_upper.startswith("SHOW") or query_upper.startswith("DESCRIBE") or query_upper.startswith("EXPLAIN"):
            results = cursor.fetchall()
            # 将结果转为字典列表
            dict_results = [dict(row) for row in results]
            return {
                "success": True,
                "rows": dict_results,
                "row_count": len(dict_results)
            }
        else:
            # 对于非查询性质的SQL，如INSERT, UPDATE, DELETE等
            conn.commit()
            return {
                "success": True,
                "affected_rows": cursor.rowcount
            }
    except Error as e:
        error_message = f"执行查询失败: {str(e)}"
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            error_message += "\n原因：查询中包含未知的列名"
        elif "relation" in str(e).lower() and "does not exist" in str(e).lower():
            error_message += "\n原因：查询的表不存在"
        elif "syntax error" in str(e).lower():
            error_message += "\n原因：SQL语法错误"
        return {"error": error_message, "query": query}
    except Exception as e:
        return {"error": f"执行过程中发生未知错误: {str(e)}", "query": query}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def list_tables(schema_name: str = "public", db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """列出指定模式中的所有表
    
    Args:
        schema_name: 模式名称，默认为public
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        包含表列表的字典
    """
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        
        # 查询指定模式的表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            ORDER BY table_name
        """, (schema_name,))
            
        tables = [table[0] for table in cursor.fetchall()]
        
        return {
            "success": True,
            "schema": schema_name,
            "tables": tables,
            "count": len(tables)
        }
    except Error as e:
        error_message = f"获取表列表失败: {str(e)}"
        if "permission denied" in str(e).lower():
            error_message += "\n原因：当前用户没有足够权限执行查询"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"获取表列表时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def describe_table(table_name: str, schema_name: str = "public", db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """获取表结构
    
    Args:
        table_name: 表名
        schema_name: 模式名称，默认为public
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        包含表结构信息的字典
    """
    if not table_name:
        return {"error": "表名不能为空"}
        
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 查询表结构
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                column_default,
                is_nullable
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table_name))
        
        columns = cursor.fetchall()
        
        # 获取主键信息
        cursor.execute("""
            SELECT a.attname as column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """, (f"{schema_name}.{table_name}",))
        
        primary_keys = [pk['column_name'] for pk in cursor.fetchall()]
        
        return {
            "success": True,
            "table": table_name,
            "schema": schema_name,
            "columns": [dict(col) for col in columns],
            "primary_keys": primary_keys
        }
    except Error as e:
        error_message = f"获取表结构失败: {str(e)}"
        if "does not exist" in str(e).lower():
            error_message += f"\n原因：表 {schema_name}.{table_name} 不存在"
        elif "permission denied" in str(e).lower():
            error_message += "\n原因：当前用户没有足够权限查看表结构"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"获取表结构时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def list_schemas(db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """列出数据库中的所有模式
    
    Args:
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        包含模式列表的字典
    """
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        
        # 查询所有非系统模式
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT LIKE 'pg_%' 
              AND schema_name != 'information_schema'
            ORDER BY schema_name
        """)
            
        schemas = [schema[0] for schema in cursor.fetchall()]
        
        return {
            "success": True,
            "schemas": schemas,
            "count": len(schemas)
        }
    except Error as e:
        error_message = f"获取模式列表失败: {str(e)}"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"获取模式列表时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def create_table(table_name: str, columns: List[Dict[str, Any]], schema_name: str = "public", if_not_exists: bool = True, db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """创建数据表
    
    Args:
        table_name: 表名
        columns: 列定义列表，每个列定义是一个字典，包含 name, type, nullable, default, primary_key 等字段
        schema_name: 模式名称，默认为public
        if_not_exists: 是否使用IF NOT EXISTS子句，默认为True
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        操作结果字典
    """
    if not table_name:
        return {"error": "表名不能为空"}
    
    if not columns or not isinstance(columns, list) or len(columns) == 0:
        return {"error": "列定义不能为空"}
    
    try:
        # 构建CREATE TABLE语句
        not_exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        sql = f"CREATE TABLE {not_exists_clause}{schema_name}.{table_name} ("
        
        column_defs = []
        primary_keys = []
        
        for col in columns:
            if not col.get("name") or not col.get("type"):
                return {"error": "每个列定义必须包含name和type字段"}
            
            col_def = f"{col['name']} {col['type']}"
            
            if col.get("primary_key"):
                primary_keys.append(col['name'])
            
            if col.get("nullable") is False:
                col_def += " NOT NULL"
            
            if "default" in col:
                col_def += f" DEFAULT {col['default']}"
                
            column_defs.append(col_def)
        
        # 添加主键约束
        if primary_keys:
            column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
            
        sql += ", ".join(column_defs) + ")"
        
        # 执行SQL
        conn = get_connection(db_config)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        
        return {
            "success": True,
            "message": f"表 {schema_name}.{table_name} 创建成功"
        }
    except Error as e:
        error_message = f"创建表失败: {str(e)}"
        if "already exists" in str(e).lower():
            error_message += f"\n原因：表 {schema_name}.{table_name} 已存在"
        elif "syntax error" in str(e).lower():
            error_message += "\n原因：SQL语法错误，请检查列定义"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"创建表时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def insert_data(table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], schema_name: str = "public", db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """向表中插入数据
    
    Args:
        table_name: 表名
        data: 要插入的数据，可以是单条记录(字典)或多条记录(字典列表)
        schema_name: 模式名称，默认为public
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        操作结果字典
    """
    if not table_name:
        return {"error": "表名不能为空"}
    
    if not data:
        return {"error": "插入数据不能为空"}
    
    # 确保data是列表形式
    if isinstance(data, dict):
        data = [data]
    
    if not all(isinstance(item, dict) for item in data):
        return {"error": "数据格式错误，应为字典或字典列表"}
    
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        
        # 获取第一条记录的列名作为参考
        columns = list(data[0].keys())
        
        # 构建INSERT语句
        placeholders = ", ".join(["%s"] * len(columns))
        column_str = ", ".join(columns)
        
        sql = f"INSERT INTO {schema_name}.{table_name} ({column_str}) VALUES ({placeholders})"
        
        # 准备数据
        values = []
        for item in data:
            row_values = [item.get(col) for col in columns]
            values.append(row_values)
        
        # 执行批量插入
        cursor.executemany(sql, values)
        conn.commit()
        
        return {
            "success": True,
            "affected_rows": len(data),
            "message": f"成功向表 {schema_name}.{table_name} 插入 {len(data)} 条数据"
        }
    except Error as e:
        error_message = f"插入数据失败: {str(e)}"
        if "does not exist" in str(e).lower():
            error_message += f"\n原因：表 {schema_name}.{table_name} 不存在"
        elif "violates" in str(e).lower() and "constraint" in str(e).lower():
            error_message += "\n原因：违反表约束条件"
        elif "column" in str(e).lower() and "does not exist" in str(e).lower():
            error_message += "\n原因：表中不存在指定的列"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"插入数据时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

@mcp.tool()
async def update_data(table_name: str, data: Dict[str, Any], condition: str, params: Optional[List[Any]] = None, schema_name: str = "public", db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """更新表中的数据
    
    Args:
        table_name: 表名
        data: 要更新的数据字段和值
        condition: WHERE条件语句
        params: 条件参数，用于参数化查询防止SQL注入
        schema_name: 模式名称，默认为public
        db_config: 数据库连接配置参数，如果为None则使用默认配置
        
    Returns:
        操作结果字典
    """
    if not table_name:
        return {"error": "表名不能为空"}
    
    if not data or not isinstance(data, dict):
        return {"error": "更新数据不能为空且必须是字典格式"}
    
    if not condition:
        return {"error": "更新条件不能为空，为了安全起见，必须提供WHERE条件"}
    
    try:
        conn = get_connection(db_config)
        cursor = conn.cursor()
        
        # 构建SET子句
        set_items = []
        set_values = []
        
        for key, value in data.items():
            set_items.append(f"{key} = %s")
            set_values.append(value)
        
        set_clause = ", ".join(set_items)
        
        # 构建完整SQL语句
        sql = f"UPDATE {schema_name}.{table_name} SET {set_clause} WHERE {condition}"
        
        # 合并参数
        all_params = set_values
        if params:
            all_params.extend(params)
        
        # 执行更新
        cursor.execute(sql, all_params)
        affected_rows = cursor.rowcount
        conn.commit()
        
        return {
            "success": True,
            "affected_rows": affected_rows,
            "message": f"成功更新表 {schema_name}.{table_name} 中的 {affected_rows} 条数据"
        }
    except Error as e:
        error_message = f"更新数据失败: {str(e)}"
        if "does not exist" in str(e).lower():
            error_message += f"\n原因：表 {schema_name}.{table_name} 不存在"
        elif "column" in str(e).lower() and "does not exist" in str(e).lower():
            error_message += "\n原因：尝试更新不存在的列"
        elif "syntax error" in str(e).lower():
            error_message += "\n原因：SQL语法错误，请检查条件语句"
        return {"error": error_message}
    except Exception as e:
        return {"error": f"更新数据时发生未知错误: {str(e)}"}
    finally:
        if 'conn' in locals() and not conn.closed:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # 初始化全局配置
    GLOBAL_DB_CONFIG = get_config_from_args()
    
    # 启动MCP服务器
    mcp.run() 