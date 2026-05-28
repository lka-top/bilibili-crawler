# -*- coding: utf-8 -*-
"""
B站视频数据采集工具 - 主程序入口

综合实战项目：B站视频数据采集与分析工具

功能特点：
- 多种登录方式（扫码登录 / Cookie 登录）
- 反检测浏览器自动化（Playwright + stealth.js）
- WBI 签名算法支持（B站 API 签名）
- 视频搜索和详情获取
- 多格式数据存储（JSON / CSV）
- 词云和统计报告自动生成

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler

使用方法：
    python main.py                              # 交互模式，终端选择模式和参数
    python main.py -k "关键词1,关键词2"          # 关键词搜索模式
    python main.py -b "BV1xx411c7mD"            # 视频号模式
    python main.py --help                       # 查看完整帮助
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入各模块
from config import settings, CrawlerType
from crawler.spider import BilibiliCrawler
from store.backend import StorageManager
from analysis.report import ReportGenerator, generate_report
from models.bilibili import BilibiliVideo


# 配置日志
def setup_logger():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{message}</cyan>",
        level="INFO"
    )
    logger.add(
        "logs/bilibili_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8"
    )


async def run_crawler() -> List[BilibiliVideo]:
    """
    运行爬虫

    完整流程：
    1. 启动浏览器
    2. 执行登录（扫码或Cookie）
    3. 初始化 API 客户端（获取 WBI 密钥）
    4. 根据配置执行爬取（搜索或指定视频）
    5. 返回爬取结果

    Returns:
        List[BilibiliVideo]: 爬取的视频列表
    """
    crawler = BilibiliCrawler()
    return await crawler.start()


async def save_data(videos: List[BilibiliVideo], output_dir: str = None, filename: str = None) -> str:
    if not videos:
        logger.warning("没有数据需要保存")
        return ""

    data = [video.to_dict() for video in videos]

    storage_dir = output_dir or settings.storage_output_dir
    storage = StorageManager(
        storage_type=settings.storage_type.value,
        output_dir=storage_dir,
        filename=filename
    )

    success = await storage.save(data)

    if success:
        return str(storage.filepath)
    return ""


def generate_analysis_report(
    videos: List[BilibiliVideo],
    output_dir: str = None,#type:ignore
    report_filename: str = "report.md",
    wordcloud_filename: str = "title_wordcloud.png"
) -> str:
    if not videos:
        logger.warning("没有数据，跳过报告生成")
        return ""

    report_dir = output_dir or settings.storage_output_dir
    report_path = generate_report(
        videos=videos,#type:ignore
        output_dir=report_dir,
        font_path='MSYH.TTC',
        report_filename=report_filename,
        wordcloud_filename=wordcloud_filename
    )

    return report_path


async def main():
    """主函数"""

    # 打印欢迎信息
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           B站视频数据采集与分析工具 v2.0                 ║
    ║                                                          ║
    ║  功能：                                                  ║
    ║  - 视频搜索与详情获取                                    ║
    ║  - 扫码登录 / Cookie 登录                                ║
    ║  - JSON / CSV 数据存储                                   ║
    ║  - 词云和统计分析报告                                    ║
    ║                                                          ║
    ║  参考项目：MediaCrawler                                  ║
    ║  注意：请遵守 B站的使用条款和法律法规                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # 显示当前配置
    logger.info(f"启动 {settings.app_name}")
    logger.info(f"爬取类型: {settings.crawler_type.value}")
    logger.info(f"登录方式: {settings.login_type.value}")
    logger.info(f"最大数量: {settings.max_video_count}")
    logger.info(f"存储类型: {settings.storage_type.value}")

    if settings.crawler_type == CrawlerType.SEARCH:
        logger.info(f"搜索关键词: {settings.keywords}")
    else:
        logger.info(f"指定视频: {len(settings.specified_id_list)} 个")

    logger.info("=" * 50)

    try:
        # 1. 运行爬虫
        logger.info("开始爬取数据...")
        videos = await run_crawler()
        logger.info(f"爬取完成: {len(videos)} 条视频")

        if not videos:
            logger.warning("没有爬取到数据，退出")
            return

        # 2. 保存数据 & 3. 生成报告
        data_paths = []
        report_paths = []

        if settings.crawler_type == CrawlerType.SEARCH and settings.keywords:
            # 关键词模式：所有视频保存在同一个关键词目录下
            kw = settings.keywords.split(",")[0].strip()
            output_dir = f"{settings.storage_output_dir}/{kw}_results"
            filename = f"{kw}.json"
            report_filename = f"{kw}.md"
            wordcloud_filename = f"{kw}.png"

            logger.info("保存数据...")
            data_path = await save_data(videos, output_dir=output_dir, filename=filename)
            if data_path:
                data_paths.append(data_path)
                logger.info(f"数据已保存: {data_path}")

            logger.info("生成分析报告...")
            report_path = generate_analysis_report(
                videos, output_dir=output_dir,
                report_filename=report_filename,
                wordcloud_filename=wordcloud_filename
            )
            if report_path:
                report_paths.append(report_path)
                logger.info(f"报告已生成: {report_path}")
        else:
            # 视频号模式：每个 BV 号独立一个目录
            for video in videos:
                bvid = video.bvid
                output_dir = f"{settings.storage_output_dir}/{bvid}_results"
                filename = f"{bvid}.json"
                report_filename = f"{bvid}.md"
                wordcloud_filename = f"{bvid}.png"

                logger.info(f"保存 {bvid} 数据...")
                data_path = await save_data([video], output_dir=output_dir, filename=filename)
                if data_path:
                    data_paths.append(data_path)
                    logger.info(f"数据已保存: {data_path}")

                logger.info(f"生成 {bvid} 分析报告...")
                report_path = generate_analysis_report(
                    [video], output_dir=output_dir,
                    report_filename=report_filename,
                    wordcloud_filename=wordcloud_filename
                )
                if report_path:
                    report_paths.append(report_path)
                    logger.info(f"报告已生成: {report_path}")

        # 4. 打印结果摘要
        logger.info("=" * 50)
        logger.info("任务完成！")
        logger.info(f"爬取视频: {len(videos)} 个")
        for dp in data_paths:
            logger.info(f"数据文件: {dp}")
        for rp in report_paths:
            logger.info(f"分析报告: {rp}")
        logger.info("=" * 50)

        # 打印部分结果预览
        print("\n视频预览（前 5 条）:")
        print("-" * 60)
        for i, video in enumerate(videos[:5], 1):
            print(f"{i}. {video.title[:40]}...")
            print(f"   UP主: {video.nickname}")
            print(f"   播放: {video.play_count:,}  点赞: {video.liked_count:,}")
            print()

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
    except Exception as e:
        logger.exception(f"执行出错: {e}")
        raise


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="B站视频数据采集与分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                              # 交互模式，终端选择模式
  python main.py -k "原神,星穹铁道"            # 关键词搜索模式
  python main.py --keyword "高考"              # 关键词搜索模式（长选项）
  python main.py -b BV1xx411c7mD              # 视频号模式（单个BV号）
  python main.py -b BV1xx,BV2yy,BV3zz         # 视频号模式（多个BV号）
  python main.py --bvid BV1xx411c7mD          # 视频号模式（长选项）
        """
    )

    parser.add_argument(
        "-k", "--keyword",
        type=str,
        default=None,
        help="关键词搜索模式：指定搜索关键词，多个关键词用逗号分隔（例如：-k \"原神,星穹铁道\"）"
    )
    parser.add_argument(
        "-b", "--bvid",
        type=str,
        default=None,
        help="视频号模式：指定视频BV号，多个BV号用逗号分隔（例如：-b BV1xx411c7mD 或 -b \"BV1xx,BV2yy\"）"
    )

    return parser.parse_args()


def interactive_mode():
    """交互模式：终端选择爬取模式和参数"""
    print("\n" + "=" * 50)
    print("  请选择爬取模式:")
    print("=" * 50)
    print("  [1] 关键词搜索模式")
    print("  [2] 视频号模式（按BV号获取视频详情）")
    print("=" * 50)

    while True:
        choice = input("\n请输入选项 (1 或 2): ").strip()
        if choice == "1":
            keywords = input("请输入搜索关键词（多个关键词用逗号分隔）: ").strip()
            if not keywords:
                print("关键词不能为空，请重新输入。")
                continue
            return "search", keywords
        elif choice == "2":
            bvids = input("请输入视频BV号（多个BV号用逗号分隔）: ").strip()
            if not bvids:
                print("BV号不能为空，请重新输入。")
                continue
            return "detail", bvids
        else:
            print("无效选项，请输入 1 或 2。")


def cli():
    """命令行入口"""
    # 解析命令行参数
    args = parse_args()

    # 判断模式
    if args.keyword is not None:
        # 关键词搜索模式
        mode = "search"
        param = args.keyword
    elif args.bvid is not None:
        # 视频号模式
        mode = "detail"
        param = args.bvid
    else:
        # 交互模式
        mode, param = interactive_mode()

    # 根据模式覆盖配置
    if mode == "search":
        settings.crawler_type = CrawlerType.SEARCH
        settings.keywords = param
        logger.info(f"关键词搜索模式，关键词: {param}")
    elif mode == "detail":
        settings.crawler_type = CrawlerType.DETAIL
        # 将逗号分隔的BV号转换为列表
        bvid_list = [bvid.strip() for bvid in param.split(",") if bvid.strip()]
        settings.specified_id_list = bvid_list
        logger.info(f"视频号模式，BV号: {bvid_list}")

    # 设置日志
    setup_logger()

    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path(settings.storage_output_dir).mkdir(parents=True, exist_ok=True)

    # 运行主程序
    asyncio.run(main())


if __name__ == "__main__":
    cli()
