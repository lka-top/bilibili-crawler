# -*- coding: utf-8 -*-
"""
数据存储后端模块

本模块实现了多种数据存储后端，包括：
- JSONStorage: JSON 文件存储
- CSVStorage: CSV 文件存储
- StorageManager: 统一存储管理器

支持保存 BilibiliVideo 模型数据，自动转换为适合存储的格式。

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler/blob/main/store/bilibili/_store_impl.py
"""

import json
import csv
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from loguru import logger

# 尝试导入模型
try:
    from models.bilibili import BilibiliVideo
    HAS_MODEL = True
except ImportError:
    HAS_MODEL = False


class BaseStorage(ABC):
    """存储基类"""

    @abstractmethod
    async def save(self, data: List[Dict]) -> bool:
        """保存数据"""
        pass

    @abstractmethod
    async def load(self) -> List[Dict]:
        """加载数据"""
        pass

    def _convert_to_dict(self, item: Any) -> Dict:
        """
        将对象转换为字典

        支持 BilibiliVideo 模型和普通字典。
        """
        if HAS_MODEL and isinstance(item, BilibiliVideo):
            return item.to_dict()
        elif hasattr(item, 'model_dump'):
            return item.model_dump()
        elif hasattr(item, 'dict'):
            return item.dict()
        elif isinstance(item, dict):
            return item
        else:
            return dict(item)


class JSONStorage(BaseStorage):
    """JSON 存储"""

    def __init__(self, output_dir: str, filename: str = None): # type: ignore
        """
        初始化 JSON 存储

        Args:
            output_dir: 输出目录
            filename: 文件名（可选，默认按时间戳生成）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            self.filepath = self.output_dir / filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filepath = self.output_dir / f"data_{timestamp}.json"

    async def save(self, data: List[Dict]) -> bool:
        """保存数据到 JSON 文件"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到: {self.filepath} ({len(data)} 条)")
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    async def load(self) -> List[Dict]:
        """从 JSON 文件加载数据"""
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载失败: {e}")
            return []

    async def append(self, data: Dict) -> bool:
        """追加单条数据"""
        existing = await self.load()
        existing.append(data)
        return await self.save(existing)

    async def append_batch(self, data: List[Dict]) -> bool:
        """追加多条数据"""
        existing = await self.load()
        existing.extend(data)
        return await self.save(existing)


class CSVStorage(BaseStorage):
    """CSV 存储"""

    def __init__(
        self,
        output_dir: str,
        filename: str = None,#type:ignore
        fields: List[str] = None#type:ignore
    ):
        """
        初始化 CSV 存储

        Args:
            output_dir: 输出目录
            filename: 文件名（可选）
            fields: 字段列表（可选，默认从数据推断）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            self.filepath = self.output_dir / filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.filepath = self.output_dir / f"data_{timestamp}.csv"

        self.fields = fields

    async def save(self, data: List[Dict]) -> bool:
        """保存数据到 CSV 文件"""
        if not data:
            logger.warning("没有数据需要保存")
            return True

        try:
            # 确定字段列表
            fields = self.fields or list(data[0].keys())

            with open(self.filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)

            logger.info(f"数据已保存到: {self.filepath} ({len(data)} 条)")
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    async def load(self) -> List[Dict]:
        """从 CSV 文件加载数据"""
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            logger.error(f"加载失败: {e}")
            return []


class MysqlManager:
    """MySQL 存储管理器

    关键词模式：每个关键词一张表（kw_<关键词>），全量替换旧数据
    视频号模式：固定表 t_video_detail，追加写入
    """

    _TABLE_DETAIL = 't_video_detail'

    # 共用的列定义
    _COL_DEF = (
        'id INT AUTO_INCREMENT PRIMARY KEY, '
        'bvid VARCHAR(20) NOT NULL, '
        'video_id VARCHAR(30) DEFAULT "", '
        'title VARCHAR(500) DEFAULT "", '
        '`desc` TEXT, '
        'cover_url VARCHAR(300) DEFAULT "", '
        'duration INT DEFAULT 0, '
        'create_time BIGINT DEFAULT 0, '
        'pubdate_str VARCHAR(20) DEFAULT "", '
        'user_id BIGINT DEFAULT 0, '
        'nickname VARCHAR(100) DEFAULT "", '
        'avatar VARCHAR(300) DEFAULT "", '
        'play_count INT DEFAULT 0, '
        'danmaku_count INT DEFAULT 0, '
        'comment_count INT DEFAULT 0, '
        'liked_count INT DEFAULT 0, '
        'coin_count INT DEFAULT 0, '
        'favorite_count INT DEFAULT 0, '
        'share_count INT DEFAULT 0, '
        'video_url VARCHAR(200) DEFAULT "", '
        'tname VARCHAR(50) DEFAULT "", '
        'crawl_time VARCHAR(20) DEFAULT ""'
    )

    # data dict keys → table columns
    _DATA_COLS = [
        'bvid', 'video_id', 'title', 'desc', 'cover_url', 'duration',
        'create_time', 'pubdate_str', 'user_id', 'nickname', 'avatar',
        'play_count', 'danmaku_count', 'comment_count', 'liked_count',
        'coin_count', 'favorite_count', 'share_count', 'video_url',
        'tname', 'crawl_time',
    ]

    def __init__(self):
        from store.mysql import MySQLDatabase
        self._db = MySQLDatabase()

    @staticmethod
    def _keyword_table(keyword: str) -> str:
        return f'kw_{keyword}'

    def _ensure_table(self, table: str):
        """表不存在则创建"""
        if not self._db.table_exists(table):
            self._db.create_table(table, self._COL_DEF)

    def save_keyword(self, keyword: str, data: list[dict]) -> int:
        """关键词模式：删表重建，全量替换。返回写入行数。"""
        table = self._keyword_table(keyword)
        # 全量替换：先删再建
        self._db.drop_table(table)
        self._db.create_table(table, self._COL_DEF)

        if not data:
            return 0

        rows = [{k: item.get(k, '') for k in self._DATA_COLS} for item in data]
        count = self._db.insert_batch(table, rows)
        logger.info(f'关键词 "{keyword}" → 表 {table}，写入 {count} 条（全量替换）')
        return count

    def save_detail(self, data: list[dict]) -> int:
        """视频号模式：表不存在则创建，追加写入。返回写入行数。"""
        self._ensure_table(self._TABLE_DETAIL)

        if not data:
            return 0

        rows = [{k: item.get(k, '') for k in self._DATA_COLS} for item in data]
        count = self._db.insert_batch(self._TABLE_DETAIL, rows)
        logger.info(f'视频详情 → 表 {self._TABLE_DETAIL}，追加 {count} 条')
        return count

    def close(self):
        self._db.close()


class MySQLStorage:
    """MySQL 存储适配器，包装 MysqlManager 提供 async 接口"""

    def __init__(self):
        self._manager = MysqlManager()

    async def save(self, data: list[dict], keyword: str = '') -> int:
        """保存数据到 MySQL，根据 keyword 分流"""
        import asyncio
        if keyword:
            return await asyncio.to_thread(self._manager.save_keyword, keyword, data)
        else:
            return await asyncio.to_thread(self._manager.save_detail, data)

    async def load(self) -> list[dict]:
        return []

    @property
    def filepath(self) -> str:
        return ""


class StorageManager:
    """存储管理器"""

    def __init__(
        self,
        storage_type: str,
        output_dir: str,
        filename: str = None,#type:ignore
        **kwargs
    ):
        """
        初始化存储管理器

        Args:
            storage_type: 存储类型 ('json', 'csv', 'mysql')
            output_dir: 输出目录（mysql 类型忽略）
            filename: 文件名（mysql 类型忽略）
            **kwargs: 传递给具体存储类的参数
        """
        self.output_dir = output_dir

        if storage_type == 'json':
            self._storage = JSONStorage(output_dir, filename)
        elif storage_type == 'csv':
            self._storage = CSVStorage(output_dir, filename, **kwargs)
        elif storage_type == 'mysql':
            self._storage = MySQLStorage()
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")

        self.storage_type = storage_type
        logger.info(f"存储管理器初始化: {storage_type} -> {output_dir}")

    async def save(self, data: List[Dict], **kwargs) -> bool:
        """保存数据"""
        return await self._storage.save(data, **kwargs)

    async def load(self) -> List[Dict]:
        """加载数据"""
        return await self._storage.load()

    @property
    def filepath(self) -> Path:
        """获取文件路径"""
        return self._storage.filepath
