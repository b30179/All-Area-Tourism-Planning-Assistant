"""测试 src.tools.poi POI 模块"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.tools.poi import (
    POI_TOOL_SCHEMA,
    _format_tencent_poi,
    _format_baidu_poi,
)


class TestPOISchema:
    """POI 工具 Schema"""

    def test_schema_structure(self):
        assert POI_TOOL_SCHEMA["type"] == "function"
        assert POI_TOOL_SCHEMA["function"]["name"] == "search_poi"

    def test_schema_required_params(self):
        params = POI_TOOL_SCHEMA["function"]["parameters"]
        assert "query" in params["required"]
        assert "region" in params["required"]


class TestFormatTencentPOI:
    """腾讯 POI 格式化"""

    def test_basic_format(self):
        poi = _format_tencent_poi({
            "title": "广州塔",
            "address": "广州市海珠区",
            "tel": "020-12345678",
            "category": "景点",
            "location": {"lat": 23.1, "lng": 113.3},
        })
        assert poi["name"] == "广州塔"
        assert poi["address"] == "广州市海珠区"
        assert poi["tel"] == "020-12345678"
        assert poi["category"] == "景点"
        assert poi["location"]["lat"] == 23.1

    def test_missing_tel(self):
        poi = _format_tencent_poi({"title": "无名", "location": {}})
        assert poi["tel"] == "暂无"

    def test_missing_location(self):
        poi = _format_tencent_poi({"title": "X", "location": {}})
        assert poi["location"]["lat"] == 0.0
        assert poi["location"]["lng"] == 0.0


class TestFormatBaiduPOI:
    """百度 POI 格式化"""

    def test_basic_format(self):
        poi = _format_baidu_poi({
            "name": "故宫",
            "address": "北京市东城区",
            "telephone": "010-12345678",
            "detail_info": {"tag": "景点", "type": "旅游"},
            "location": {"lat": 39.9, "lng": 116.4},
        })
        assert poi["name"] == "故宫"
        assert poi["category"] == "景点"
        assert poi["location"]["lat"] == 39.9

    def test_category_from_tag(self):
        poi = _format_baidu_poi({
            "name": "X",
            "detail_info": {"tag": "美食", "type": "餐饮"},
            "location": {"lat": 0, "lng": 0},
        })
        assert poi["category"] == "美食"

    def test_category_fallback_to_type(self):
        poi = _format_baidu_poi({
            "name": "Y",
            "detail_info": {"type": "购物"},
            "location": {"lat": 0, "lng": 0},
        })
        assert poi["category"] == "购物"

    def test_category_fallback_to_detail(self):
        poi = _format_baidu_poi({
            "name": "Z",
            "detail": "123",
            "location": {"lat": 0, "lng": 0},
        })
        # detail_info 不存在的回退
        assert poi["category"] == "123"

    def test_no_detail_info_no_detail(self):
        poi = _format_baidu_poi({
            "name": "W",
            "location": {"lat": 0, "lng": 0},
        })
        assert poi["category"] == ""

    def test_missing_telephone(self):
        poi = _format_baidu_poi({
            "name": "Q",
            "location": {"lat": 0, "lng": 0},
        })
        assert poi["tel"] == "暂无"
