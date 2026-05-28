# -*- coding: utf-8 -*-
"""
视频号爬取功能测试用例

测试范围:
- parse_video_info_from_url: BV 号 / URL 解析
- BilibiliVideo 模型: API 响应解析、序列化
- BilibiliSign: WBI 签名算法
- BilibiliClient.get_video_info: 视频详情 API（mock HTTP）
- BilibiliClient.search_video_by_keyword: 搜索 API（mock HTTP）
- BilibiliCrawler.get_specified_videos: 指定视频爬取（集成 mock）
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from tools.sign import (
    BilibiliSign,
    extract_wbi_keys_from_urls,
    parse_video_info_from_url,
    parse_creator_info_from_url,
    VideoUrlInfo,
)
from models.bilibili import BilibiliVideo


# ==================== Mock 数据 ====================

MOCK_VIDEO_DETAIL_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "aid": 123456789,
        "bvid": "BV1xx411c7mD",
        "title": "Python 异步编程实战教程",
        "desc": "深入讲解 Python asyncio 的原理与实践",
        "pic": "https://i0.hdslb.com/bfs/archive/abc123.jpg",
        "duration": 1842,
        "pubdate": 1700000000,
        "owner": {
            "mid": 54321,
            "name": "Python大师",
            "face": "https://i0.hdslb.com/bfs/face/avatar123.jpg",
        },
        "stat": {
            "view": 158000,
            "danmaku": 3200,
            "reply": 890,
            "like": 12500,
            "coin": 6800,
            "favorite": 9500,
            "share": 2100,
        },
        "tname": "编程",
    },
}

MOCK_SEARCH_RESPONSE = {
    "code": 0,
    "message": "0",
    "data": {
        "seid": "abc123",
        "page": 1,
        "pagesize": 20,
        "numResults": 100,
        "numPages": 5,
        "result": [
            {
                "aid": 111,
                "bvid": "BV1aa1111111",
                "title": "Python 入门教程",
                "description": "从零开始学 Python",
                "pic": "//i0.hdslb.com/bfs/archive/thumb1.jpg",
                "duration": "15:30",
                "pubdate": 1700000100,
                "mid": 1001,
                "author": "教程UP",
                "play": 50000,
                "danmaku": 800,
                "review": 300,
                "like": 2000,
                "favorites": 1500,
                "typename": "编程",
            },
            {
                "aid": 222,
                "bvid": "BV2bb2222222",
                "title": '高级<em class="keyword">Python</em>技巧',
                "description": "进阶内容",
                "pic": "//i0.hdslb.com/bfs/archive/thumb2.jpg",
                "duration": "1:02:45",
                "pubdate": 1700000200,
                "mid": 2002,
                "author": "进阶UP",
                "play": 30000,
                "danmaku": 600,
                "review": 200,
                "like": 1500,
                "favorites": 1200,
                "typename": "编程",
            },
        ],
    },
}

# 付费视频（无 aid/bvid）
MOCK_SEARCH_WITH_PAY_ONLY = {
    "code": 0,
    "message": "0",
    "data": {
        "seid": "xyz",
        "page": 1,
        "pagesize": 20,
        "numResults": 1,
        "numPages": 1,
        "result": [
            {
                "title": "付费课程-深度学习",
                "description": "付费内容",
                "pic": "//i0.hdslb.com/bfs/archive/pay.jpg",
                "duration": "2:00:00",
                "pubdate": 1700000300,
                "mid": 3003,
                "author": "付费UP",
                "play": 1000,
                "typename": "课程",
            },
        ],
    },
}


# ==================== URL 解析测试 ====================


class TestVideoUrlParsing(unittest.TestCase):
    """BV 号与视频 URL 解析测试"""

    def test_parse_bv_direct(self):
        """直接传入 BV 号"""
        result = parse_video_info_from_url("BV1d54y1g7db")
        self.assertEqual(result.video_id, "BV1d54y1g7db")

    def test_parse_bv_with_prefix_BV(self):
        """BV 号以 BV 开头"""
        result = parse_video_info_from_url("BV1xx411c7mD")
        self.assertEqual(result.video_id, "BV1xx411c7mD")

    def test_parse_full_url(self):
        """完整 B站视频 URL"""
        result = parse_video_info_from_url(
            "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387"
        )
        self.assertEqual(result.video_id, "BV1dwuKzmE26")

    def test_parse_url_no_query(self):
        """不带查询参数的 URL"""
        result = parse_video_info_from_url("https://www.bilibili.com/video/BV1d54y1g7db")
        self.assertEqual(result.video_id, "BV1d54y1g7db")

    def test_parse_url_with_short_link(self):
        """b23.tv 短链接无法解析，应抛出异常"""
        with self.assertRaises(ValueError):
            parse_video_info_from_url("https://b23.tv/abcd123")

    def test_parse_non_bilibili_url(self):
        """非 B站 URL"""
        with self.assertRaises(ValueError):
            parse_video_info_from_url("https://www.youtube.com/watch?v=abcd1234")

    def test_parse_empty_string(self):
        """空字符串"""
        with self.assertRaises(ValueError):
            parse_video_info_from_url("")


# ==================== BilibiliVideo 模型测试 ====================


class TestBilibiliVideoModel(unittest.TestCase):
    """BilibiliVideo 数据模型测试"""

    def test_from_api_response_basic(self):
        """从 API 响应创建视频模型"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])

        self.assertEqual(video.video_id, "123456789")
        self.assertEqual(video.bvid, "BV1xx411c7mD")
        self.assertEqual(video.title, "Python 异步编程实战教程")
        self.assertEqual(video.desc, "深入讲解 Python asyncio 的原理与实践")
        self.assertEqual(video.duration, 1842)
        self.assertEqual(video.user_id, 54321)
        self.assertEqual(video.nickname, "Python大师")

    def test_from_api_response_stats(self):
        """验证统计数据正确解析"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])

        self.assertEqual(video.play_count, 158000)
        self.assertEqual(video.danmaku_count, 3200)
        self.assertEqual(video.comment_count, 890)
        self.assertEqual(video.liked_count, 12500)
        self.assertEqual(video.coin_count, 6800)
        self.assertEqual(video.favorite_count, 9500)
        self.assertEqual(video.share_count, 2100)

    def test_from_api_response_auto_url(self):
        """验证自动生成 video_url"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        self.assertEqual(video.video_url, "https://www.bilibili.com/video/BV1xx411c7mD")

    def test_from_api_response_auto_crawl_time(self):
        """验证自动设置爬取时间"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        self.assertIsNotNone(video.crawl_time)
        self.assertIn("-", video.crawl_time)

    def test_from_api_response_auto_pubdate(self):
        """验证自动格式化发布时间"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        # 1700000000 = 2023-11-14 22:13:20 UTC
        self.assertIn("2023", video.pubdate_str)

    def test_from_api_response_source_keyword(self):
        """验证搜索关键词传递"""
        video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"], source_keyword="Python"
        )
        self.assertEqual(video.source_keyword, "Python")

    def test_from_api_response_tname(self):
        """验证分区名称"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        self.assertEqual(video.tname, "编程")

    def test_from_search_result_basic(self):
        """从搜索结果创建视频模型"""
        item = MOCK_SEARCH_RESPONSE["data"]["result"][0]
        video = BilibiliVideo.from_search_result(item, "Python")

        self.assertEqual(video.video_id, "111")
        self.assertEqual(video.bvid, "BV1aa1111111")
        self.assertEqual(video.title, "Python 入门教程")
        self.assertEqual(video.play_count, 50000)
        self.assertEqual(video.nickname, "教程UP")

    def test_from_search_result_html_title_cleaned(self):
        """搜索结果中的 HTML 标签应被清除"""
        item = MOCK_SEARCH_RESPONSE["data"]["result"][1]
        video = BilibiliVideo.from_search_result(item, "Python")
        # <em class="keyword">Python</em> 应被移除
        self.assertNotIn("<em", video.title)
        self.assertEqual(video.title, "高级Python技巧")

    def test_duration_parsing_mm_ss(self):
        """时长解析: 分:秒"""
        result = BilibiliVideo._parse_duration("15:30")
        self.assertEqual(result, 930)  # 15*60 + 30

    def test_duration_parsing_hh_mm_ss(self):
        """时长解析: 时:分:秒"""
        result = BilibiliVideo._parse_duration("1:02:45")
        self.assertEqual(result, 3765)  # 3600 + 120 + 45

    def test_duration_parsing_int(self):
        """时长解析: 直接传入整数"""
        result = BilibiliVideo._parse_duration(600)
        self.assertEqual(result, 600)

    def test_duration_parsing_invalid(self):
        """时长解析: 无效输入"""
        result = BilibiliVideo._parse_duration("invalid")
        self.assertEqual(result, 0)

    def test_to_dict(self):
        """测试序列化为 dict"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        d = video.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["bvid"], "BV1xx411c7mD")
        self.assertEqual(d["title"], "Python 异步编程实战教程")

    def test_to_csv_row(self):
        """测试 CSV 行格式"""
        video = BilibiliVideo.from_api_response(MOCK_VIDEO_DETAIL_RESPONSE["data"])
        row = video.to_csv_row()
        self.assertEqual(row["BV号"], "BV1xx411c7mD")
        self.assertEqual(row["标题"], "Python 异步编程实战教程")
        self.assertEqual(row["UP主"], "Python大师")
        self.assertEqual(row["播放量"], 158000)
        self.assertIn("视频链接", row)

    def test_csv_row_long_desc_truncated(self):
        """长描述在 CSV 中应被截断"""
        data = {**MOCK_VIDEO_DETAIL_RESPONSE["data"]}
        data["desc"] = "A" * 200
        video = BilibiliVideo.from_api_response(data)
        row = video.to_csv_row()
        self.assertLess(len(row["描述"]), 150)
        self.assertTrue(row["描述"].endswith("..."))


# ==================== WBI 签名测试 ====================


class TestWbiSign(unittest.TestCase):
    """WBI 签名算法测试"""

    def setUp(self):
        self.img_key = "7cd084941338484aae1ad9425b84077c"
        self.sub_key = "4932caff0ff746eab6f01bf08b70ac45"

    def test_extract_keys_from_url(self):
        """从完整 URL 提取 key"""
        img_url = f"https://i0.hdslb.com/bfs/wbi/{self.img_key}.png"
        sub_url = f"https://i0.hdslb.com/bfs/wbi/{self.sub_key}.png"
        ik, sk = extract_wbi_keys_from_urls(img_url, sub_url)
        self.assertEqual(ik, self.img_key)
        self.assertEqual(sk, self.sub_key)

    def test_get_salt_length(self):
        """salt 长度应为 32"""
        signer = BilibiliSign(self.img_key, self.sub_key)
        salt = signer.get_salt()
        self.assertEqual(len(salt), 32)

    def test_sign_adds_wts_and_wrid(self):
        """签名后应包含 wts 和 w_rid"""
        signer = BilibiliSign(self.img_key, self.sub_key)
        params = {"keyword": "Python教程", "page": 1}
        signed = signer.sign(params)

        self.assertIn("wts", signed)
        self.assertIn("w_rid", signed)
        self.assertIn("keyword", signed)

    def test_sign_wrid_length(self):
        """w_rid 应该是 32 位 MD5 哈希"""
        signer = BilibiliSign(self.img_key, self.sub_key)
        params = {"keyword": "测试", "search_type": "video"}
        signed = signer.sign(params)
        self.assertEqual(len(signed["w_rid"]), 32)

    def test_sign_deterministic_for_same_timestamp(self):
        """相同参数和时间戳应产生相同签名"""
        signer = BilibiliSign(self.img_key, self.sub_key)
        # 直接测试 salt 的确定性
        salt1 = signer.get_salt()
        salt2 = signer.get_salt()
        self.assertEqual(salt1, salt2)

    def test_sign_original_params_not_modified(self):
        """签名不应修改原始参数字典"""
        signer = BilibiliSign(self.img_key, self.sub_key)
        params = {"keyword": "test"}
        original = params.copy()
        signer.sign(params)
        self.assertEqual(params, original)


# ==================== BilibiliClient API 测试（Mock HTTP）====================


class TestBilibiliClientGetVideoInfo(unittest.TestCase):
    """BilibiliClient.get_video_info 测试（mock httpx）"""

    def setUp(self):
        from client.bilibili_client import BilibiliClient

        self.client = BilibiliClient()

    def _mock_response(self, status=200, json_data=None):
        """创建 mock httpx 响应"""
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        return resp

    def test_get_video_info_by_bvid(self):
        """通过 BV 号获取视频详情"""
        mock_resp = self._mock_response(json_data=MOCK_VIDEO_DETAIL_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            video = asyncio.run(self.client.get_video_info(bvid="BV1xx411c7mD"))

            self.assertIsNotNone(video)
            self.assertEqual(video.bvid, "BV1xx411c7mD")
            self.assertEqual(video.title, "Python 异步编程实战教程")
            self.assertEqual(video.play_count, 158000)
            self.assertEqual(video.nickname, "Python大师")

    def test_get_video_info_no_args_returns_none(self):
        """未提供 aid 和 bvid 应返回 None"""
        result = asyncio.run(self.client.get_video_info())
        self.assertIsNone(result)

    def test_get_video_info_api_error(self):
        """API 返回错误码"""
        error_response = {"code": -404, "message": "视频不存在"}
        mock_resp = self._mock_response(json_data=error_response)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            video = asyncio.run(self.client.get_video_info(bvid="BVnotexist"))
            self.assertIsNone(video)

    def test_get_video_info_http_error(self):
        """HTTP 请求失败"""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = self._mock_response(status=500, json_data={})

            video = asyncio.run(self.client.get_video_info(bvid="BV1xx411c7mD"))
            self.assertIsNone(video)

    def test_get_video_info_network_error(self):
        """网络异常"""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection timeout")

            video = asyncio.run(self.client.get_video_info(bvid="BV1xx411c7mD"))
            self.assertIsNone(video)


class TestBilibiliClientSearch(unittest.TestCase):
    """BilibiliClient.search_video_by_keyword 测试（mock httpx）"""

    def setUp(self):
        from client.bilibili_client import BilibiliClient

        self.client = BilibiliClient()

    def _mock_response(self, json_data):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = json_data
        return resp

    def test_search_returns_videos(self):
        """搜索返回视频列表"""
        mock_resp = self._mock_response(MOCK_SEARCH_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            videos = asyncio.run(
                self.client.search_video_by_keyword("Python", page=1)
            )

            self.assertEqual(len(videos), 2)
            self.assertEqual(videos[0].bvid, "BV1aa1111111")
            self.assertEqual(videos[0].title, "Python 入门教程")

    def test_search_filters_pay_only_videos(self):
        """付费视频（无 aid/bvid）应被过滤"""
        mock_resp = self._mock_response(MOCK_SEARCH_WITH_PAY_ONLY)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            videos = asyncio.run(
                self.client.search_video_by_keyword("深度学习", page=1)
            )

            self.assertEqual(len(videos), 0)

    def test_search_api_error(self):
        """搜索 API 返回错误"""
        error_response = {"code": -412, "message": "请求被拦截"}
        mock_resp = self._mock_response(error_response)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            videos = asyncio.run(
                self.client.search_video_by_keyword("test", page=1)
            )
            self.assertEqual(videos, [])


# ==================== 集成测试：爬虫流程 ====================


class TestCrawlerGetSpecifiedVideos(unittest.TestCase):
    """BilibiliCrawler.get_specified_videos 集成测试"""

    def setUp(self):
        from config.settings import settings, CrawlerType

        self.original_crawler_type = settings.crawler_type
        self.original_specified_ids = list(settings.specified_id_list)
        self.original_max_count = settings.max_video_count
        settings.crawler_type = CrawlerType.DETAIL

    def tearDown(self):
        from config.settings import settings

        settings.crawler_type = self.original_crawler_type
        settings.specified_id_list = self.original_specified_ids
        settings.max_video_count = self.original_max_count

    def test_get_specified_videos_single_bvid(self):
        """爬取单个 BV 号视频"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = ["BV1xx411c7mD"]

        mock_video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"]
        )

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            mock_client.get_video_info = AsyncMock(
                                return_value=mock_video
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            self.assertEqual(len(videos), 1)
                            self.assertEqual(videos[0].bvid, "BV1xx411c7mD")
                            self.assertEqual(
                                videos[0].title, "Python 异步编程实战教程"
                            )
                            mock_client.get_video_info.assert_called_once_with(
                                bvid="BV1xx411c7mD"
                            )

    def test_get_specified_videos_multiple_bvids(self):
        """爬取多个 BV 号视频"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = [
            "BV1aa1111111",
            "BV2bb2222222",
            "BV3cc3333333",
        ]

        def make_video(bvid, aid):
            data = {**MOCK_VIDEO_DETAIL_RESPONSE["data"]}
            data["bvid"] = bvid
            data["aid"] = aid
            return BilibiliVideo.from_api_response(data)

        mock_videos = [
            make_video("BV1aa1111111", 111),
            make_video("BV2bb2222222", 222),
            make_video("BV3cc3333333", 333),
        ]

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            mock_client.get_video_info = AsyncMock(
                                side_effect=mock_videos
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            self.assertEqual(len(videos), 3)
                            self.assertEqual(videos[0].bvid, "BV1aa1111111")
                            self.assertEqual(videos[1].bvid, "BV2bb2222222")
                            self.assertEqual(videos[2].bvid, "BV3cc3333333")
                            self.assertEqual(mock_client.get_video_info.call_count, 3)

    def test_get_specified_videos_with_full_urls(self):
        """支持传入完整 URL，自动解析 BV 号"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = [
            "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333",
            "BV1d54y1g7db",
        ]

        mock_video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"]
        )

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            mock_client.get_video_info = AsyncMock(
                                return_value=mock_video
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            self.assertEqual(len(videos), 2)
                            # 验证调用了正确的 bvid
                            calls = mock_client.get_video_info.call_args_list
                            self.assertEqual(calls[0].kwargs["bvid"], "BV1dwuKzmE26")
                            self.assertEqual(calls[1].kwargs["bvid"], "BV1d54y1g7db")

    def test_get_specified_videos_empty_list(self):
        """空视频列表"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = []

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        videos = asyncio.run(crawler.get_specified_videos())
                        self.assertEqual(videos, [])

    def test_get_specified_videos_respects_max_count(self):
        """达到 max_video_count 后停止爬取"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = [
            "BV1aa1111111",
            "BV2bb2222222",
            "BV3cc3333333",
            "BV4dd4444444",
            "BV5ee5555555",
        ]
        settings.max_video_count = 2

        mock_video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"]
        )

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            mock_client.get_video_info = AsyncMock(
                                return_value=mock_video
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            self.assertEqual(len(videos), 2)
                            self.assertEqual(
                                mock_client.get_video_info.call_count, 2
                            )

    def test_get_specified_videos_skips_invalid_id(self):
        """无法解析的 ID 应跳过"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = [
            "not_a_valid_id",
            "BV1xx411c7mD",
        ]

        mock_video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"]
        )

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            mock_client.get_video_info = AsyncMock(
                                return_value=mock_video
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            # 只有有效的 BV 号被爬取
                            self.assertEqual(len(videos), 1)
                            self.assertEqual(videos[0].bvid, "BV1xx411c7mD")

    def test_get_specified_videos_failed_fetch_still_continues(self):
        """某个视频获取失败时继续处理下一个"""
        from config.settings import settings
        from crawler.spider import BilibiliCrawler

        settings.specified_id_list = [
            "BV1aa1111111",
            "BV2bb2222222",
            "BV3cc3333333",
        ]

        mock_video = BilibiliVideo.from_api_response(
            MOCK_VIDEO_DETAIL_RESPONSE["data"]
        )

        crawler = BilibiliCrawler()

        with patch.object(crawler, "_init_browser", new_callable=AsyncMock):
            with patch.object(crawler, "_do_login", new_callable=AsyncMock) as mock_login:
                with patch.object(crawler, "_init_client", new_callable=AsyncMock):
                    with patch.object(crawler, "close", new_callable=AsyncMock):
                        mock_login.return_value = True

                        with patch.object(
                            crawler, "bili_client", create=True
                        ) as mock_client:
                            # 第二个返回 None
                            mock_client.get_video_info = AsyncMock(
                                side_effect=[mock_video, None, mock_video]
                            )

                            videos = asyncio.run(crawler.get_specified_videos())

                            self.assertEqual(len(videos), 2)
                            self.assertEqual(
                                mock_client.get_video_info.call_count, 3
                            )


# ==================== 运行入口 ====================

if __name__ == "__main__":
    unittest.main(verbosity=2)
