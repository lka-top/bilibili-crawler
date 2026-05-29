# -*- coding: utf-8 -*-
"""
MySQL 数据库模块

数据库名称与项目同名（bilibili_crawler），提供完整的 CRUD 操作。
"""

import pymysql
from typing import Any, Optional
from loguru import logger


class MySQLDatabase:
    """MySQL 数据库操作类，封装基本 CRUD 功能"""

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 3306,
        user: str = 'root',
        password: str = '8172616li',
        database: str = 'bilibili_crawler',
        charset: str = 'utf8mb4',
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self._conn: Optional[pymysql.Connection] = None

        self._init_database()

    def _init_database(self):
        """创建数据库（如果不存在）"""
        conn = pymysql.connect(
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            charset=self.charset,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f'CREATE DATABASE IF NOT EXISTS `{self.database}` '
                    f'DEFAULT CHARACTER SET {self.charset}'
                )
                logger.info(f'数据库 "{self.database}" 已就绪')
        finally:
            conn.close()

    @property
    def conn(self) -> pymysql.Connection:
        """获取数据库连接（懒加载，自动重连）"""
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                database=self.database, charset=self.charset,
                autocommit=False,
            )
        return self._conn

    # ── Create ──────────────────────────────────────────────

    def insert(self, table: str, data: dict) -> int:
        """
        插入单条记录

        Args:
            table: 表名
            data: 列名到值的映射

        Returns:
            自增主键 ID（如果表有自增列）

        Example:
            db.insert('video', {'bvid': 'BV1xx', 'title': '测试'})
        """
        columns = ', '.join(f'`{k}`' for k in data)
        placeholders = ', '.join(['%s'] * len(data))
        sql = f'INSERT INTO `{table}` ({columns}) VALUES ({placeholders})'

        with self.conn.cursor() as cursor:
            cursor.execute(sql, tuple(data.values()))
        self.conn.commit()

        logger.debug(f'INSERT {table}: {cursor.lastrowid}')
        return cursor.lastrowid

    def insert_batch(self, table: str, data: list[dict]) -> int:
        """
        批量插入多条记录

        Args:
            table: 表名
            data: 字典列表，所有字典必须有相同的键

        Returns:
            受影响的行数

        Example:
            db.insert_batch('video', [{'bvid': 'BV1xx'}, {'bvid': 'BV1yy'}])
        """
        if not data:
            return 0

        columns = ', '.join(f'`{k}`' for k in data[0])
        placeholders = ', '.join(['%s'] * len(data[0]))
        sql = f'INSERT INTO `{table}` ({columns}) VALUES ({placeholders})'

        rows = [tuple(d.values()) for d in data]
        with self.conn.cursor() as cursor:
            affected = cursor.executemany(sql, rows)
        self.conn.commit()

        logger.debug(f'INSERT {table}: {affected} rows')
        return affected

    # ── Read ────────────────────────────────────────────────

    def select(
        self,
        table: str,
        columns: str | tuple = '*',
        where: str = '',
        params: tuple = (),
        order_by: str = '',
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict]:
        """
        查询多条记录

        Example:
            db.select('video', where='aid > %s', params=(100,), limit=10)
        """
        col_str = ', '.join(columns) if isinstance(columns, tuple) else columns
        sql = f'SELECT {col_str} FROM `{table}`'

        if where:
            sql += f' WHERE {where}'
        if order_by:
            sql += f' ORDER BY {order_by}'
        if limit:
            sql += f' LIMIT {limit}'
        if offset:
            sql += f' OFFSET {offset}'

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def select_one(
        self,
        table: str,
        columns: str | tuple = '*',
        where: str = '',
        params: tuple = (),
    ) -> Optional[dict]:
        """查询单条记录，无结果返回 None"""
        results = self.select(table, columns, where, params, limit=1)
        return results[0] if results else None

    def count(self, table: str, where: str = '', params: tuple = ()) -> int:
        """统计记录数"""
        sql = f'SELECT COUNT(*) FROM `{table}`'
        if where:
            sql += f' WHERE {where}'

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    # ── Update ──────────────────────────────────────────────

    def update(self, table: str, data: dict, where: str, params: tuple = ()) -> int:
        """
        更新记录

        Args:
            table: 表名
            data: 要更新的列值映射
            where: WHERE 条件（不含 WHERE 关键字）
            params: WHERE 条件的参数

        Returns:
            受影响的行数

        Example:
            db.update('video', {'title': '新标题'}, 'bvid = %s', ('BV1xx',))
        """
        set_clause = ', '.join(f'`{k}` = %s' for k in data)
        sql = f'UPDATE `{table}` SET {set_clause} WHERE {where}'

        with self.conn.cursor() as cursor:
            affected = cursor.execute(sql, tuple(data.values()) + params)
        self.conn.commit()

        logger.debug(f'UPDATE {table}: {affected} rows')
        return affected

    # ── Delete ──────────────────────────────────────────────

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """
        删除记录

        Args:
            table: 表名
            where: WHERE 条件（不含 WHERE 关键字）
            params: WHERE 条件的参数

        Returns:
            受影响的行数

        Example:
            db.delete('video', 'bvid = %s', ('BV1xx',))
        """
        sql = f'DELETE FROM `{table}` WHERE {where}'

        with self.conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
        self.conn.commit()

        logger.debug(f'DELETE {table}: {affected} rows')
        return affected

    # ── Raw SQL ─────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> int:
        """执行写操作 SQL，返回受影响行数"""
        with self.conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
        self.conn.commit()
        return affected

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """执行读操作 SQL，返回结果列表"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if not rows:
                return []
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def create_table(self, table: str, columns_def: str):
        """创建表（如果不存在）"""
        sql = f'CREATE TABLE IF NOT EXISTS `{table}` ({columns_def})'
        self.execute(sql)
        logger.info(f'表 "{table}" 已就绪')

    def drop_table(self, table: str):
        """删除表"""
        self.execute(f'DROP TABLE IF EXISTS `{table}`')
        logger.info(f'表 "{table}" 已删除')

    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        result = self.query(
            'SHOW TABLES LIKE %s', (table,)
        )
        return len(result) > 0

    # ── Lifecycle ───────────────────────────────────────────

    def close(self):
        """关闭数据库连接"""
        if self._conn and self._conn.open:
            self._conn.close()
            logger.info('数据库连接已关闭')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
