# -*- coding: utf-8 -*-
"""测试 MysqlManager —— 自动识别 output 数据类型并写入对应表"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from store.backend import MysqlManager

OUTPUT_DIR = Path(__file__).parent.parent / 'output'


def load_all_output():
    """遍历 output 目录所有 JSON 文件，返回 (keyword, records) 列表"""
    all_data = []
    for json_file in OUTPUT_DIR.rglob('*.json'):
        dir_name = json_file.parent.name  # e.g. "原神_results" or "BV1xxx_results"
        keyword = dir_name.replace('_results', '')

        with open(json_file, 'r', encoding='utf-8') as f:
            records = json.load(f)
        all_data.append((keyword, records))

    return all_data


def main():
    mgr = MysqlManager()

    # 1. 清空旧数据
    mgr._db.execute(f'TRUNCATE TABLE {mgr._TABLE_KEYWORD}')
    mgr._db.execute(f'TRUNCATE TABLE {mgr._TABLE_DETAIL}')
    print('已清空旧数据\n')

    # 2. 遍历 output 目录，逐批写入
    total_kw = total_dt = 0
    for keyword, records in load_all_output():
        # 根据数据中 source_keyword 是否有值来判断类型
        kw_count = sum(1 for r in records if r.get('source_keyword'))
        dt_count = len(records) - kw_count
        total_kw += kw_count
        total_dt += dt_count

        mgr.save(records, keyword=keyword)
        print(f'[{keyword}] 关键词 {kw_count} 条, 详情 {dt_count} 条')

    # 3. 验证
    print(f'\n=== 写入汇总 ===')
    print(f'关键词视频表 (t_keyword_video): {mgr.count_keyword()} 条')
    print(f'视频详情表 (t_video_detail):   {mgr.count_detail()} 条')

    # 4. 抽样展示
    print(f'\n--- 关键词表样本 ---')
    for row in mgr.load_keyword_videos(limit=3):
        print(f'  [{row["keyword"]}] {row["title"][:50]} (播放:{row["play_count"]})')

    print(f'\n--- 详情表样本 ---')
    for row in mgr.load_detail_videos(limit=3):
        print(f'  [{row["bvid"]}] {row["title"][:50]} (播放:{row["play_count"]})')

    mgr.close()
    print('\n测试完成')


if __name__ == '__main__':
    main()
