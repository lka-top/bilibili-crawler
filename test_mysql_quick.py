# -*- coding: utf-8 -*-
"""Quick test for new MySQL storage logic."""
import asyncio
import sys
sys.path.insert(0, '.')

from config import settings, StorageType
from store.backend import StorageManager, MysqlManager


async def main():
    settings.storage_type = StorageType.MYSQL
    mgr = StorageManager(storage_type="mysql", output_dir="./output")
    assert mgr.storage_type == "mysql"
    print("[OK] StorageManager 创建 MySQL 存储")

    # ── 1. 关键词模式：写入 kw_测试关键词 ──
    kw_data = [
        {"bvid": "BV1xxTEST01", "title": "测试视频A", "desc": "描述A",
         "duration": 120, "create_time": 1700000000, "pubdate_str": "2023-11-15",
         "user_id": 100, "nickname": "UP主A",
         "play_count": 10000, "danmaku_count": 500, "comment_count": 200,
         "liked_count": 800, "coin_count": 100, "favorite_count": 300,
         "share_count": 50, "tname": "科技",
         "crawl_time": "2026-05-29 16:00:00",
         "source_keyword": "测试关键词"},
    ]

    count = await mgr.save(kw_data, keyword="测试关键词")
    print(f"[OK] 关键词写入: {count} 条")

    # 通过存储管理器内部的 manager 验证
    mysql_mgr = mgr._storage._manager
    assert mysql_mgr._db.table_exists("kw_测试关键词"), "表 kw_测试关键词 应该存在"
    print("[OK] 表 kw_测试关键词 已创建")

    # ── 2. 再次写入同一关键词 → 全量替换 ──
    kw_data2 = [
        {"bvid": "BV1xxTEST02", "title": "测试视频B", "desc": "描述B",
         "duration": 240, "create_time": 1700000001, "pubdate_str": "2023-11-16",
         "user_id": 200, "nickname": "UP主B",
         "play_count": 20000, "danmaku_count": 800, "comment_count": 300,
         "liked_count": 1200, "coin_count": 200, "favorite_count": 500,
         "share_count": 80, "tname": "游戏",
         "crawl_time": "2026-05-29 16:01:00",
         "source_keyword": "测试关键词"},
    ]

    count = await mgr.save(kw_data2, keyword="测试关键词")
    print(f"[OK] 再次写入: {count} 条")

    # 验证全量替换：应该只有 1 条（BV1xxTEST02），BV1xxTEST01 已被删除
    rows = mysql_mgr._db.select("kw_测试关键词")
    assert len(rows) == 1, f"Full replace failed: expected 1 row, got {len(rows)}"
    assert rows[0]["bvid"] == "BV1xxTEST02", f"Expected BV1xxTEST02, got {rows[0]['bvid']}"
    print("[OK] 全量替换验证通过（旧数据已清除）")

    # ── 3. 另一个关键词：独立建表 ──
    kw_data3 = [
        {"bvid": "BV1xxTEST03", "title": "测试视频C", "desc": "描述C",
         "duration": 60, "create_time": 1700000002, "pubdate_str": "2023-11-17",
         "user_id": 300, "nickname": "UP主C",
         "play_count": 5000, "danmaku_count": 100, "comment_count": 50,
         "liked_count": 300, "coin_count": 50, "favorite_count": 100,
         "share_count": 20, "tname": "生活",
         "crawl_time": "2026-05-29 16:02:00",
         "source_keyword": "其他关键词"},
    ]

    count = await mgr.save(kw_data3, keyword="其他关键词")
    print(f"[OK] 新关键词写入: {count} 条")
    assert mysql_mgr._db.table_exists("kw_其他关键词"), "表 kw_其他关键词 应该存在"
    assert mysql_mgr._db.table_exists("kw_测试关键词"), "旧表不应被影响"
    print("[OK] 独立建表验证通过")

    # ── 4. 视频号模式：追加写入 t_video_detail ──
    detail = [
        {"bvid": "BV1xxTEST04", "title": "详情视频1", "desc": "",
         "duration": 180, "create_time": 1700000003, "pubdate_str": "2023-11-18",
         "user_id": 400, "nickname": "UP主D",
         "play_count": 3000, "danmaku_count": 50, "comment_count": 30,
         "liked_count": 200, "coin_count": 30, "favorite_count": 80,
         "share_count": 10, "tname": "音乐",
         "crawl_time": "2026-05-29 16:03:00"},
    ]

    count = await mgr.save(detail)
    print(f"[OK] 视频详情写入: {count} 条")
    assert mysql_mgr._db.table_exists("t_video_detail"), "表 t_video_detail 应该存在"
    print("[OK] 表 t_video_detail 已创建")

    # 再次追加
    detail2 = [
        {"bvid": "BV1xxTEST05", "title": "详情视频2", "desc": "",
         "duration": 200, "create_time": 1700000004, "pubdate_str": "2023-11-19",
         "user_id": 500, "nickname": "UP主E",
         "play_count": 8000, "danmaku_count": 200, "comment_count": 100,
         "liked_count": 600, "coin_count": 80, "favorite_count": 200,
         "share_count": 30, "tname": "知识",
         "crawl_time": "2026-05-29 16:04:00"},
    ]

    count = await mgr.save(detail2)
    print(f"[OK] 再次追加: {count} 条")

    rows = mysql_mgr._db.select("t_video_detail")
    assert len(rows) == 2, f"Append failed: expected 2 rows, got {len(rows)}"
    print("[OK] 追加写入验证通过")

    # ── 5. Cleanup ──
    mysql_mgr._db.drop_table("kw_测试关键词")
    mysql_mgr._db.drop_table("kw_其他关键词")
    mysql_mgr._db.drop_table("t_video_detail")
    mysql_mgr.close()
    print("[OK] 测试数据已清理")
    print("\nAll tests passed!")


if __name__ == '__main__':
    asyncio.run(main())
