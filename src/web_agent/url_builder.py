"""URL構建模塊 - 負責根據參數構建搜尋URL"""

import re
import logging
from typing import Dict, Any, List

from .config import (
    SINYI_BASE_URL,
    CITY_MAPPING,
    DISTRICT_ZIP_MAPPING,
    TYPE_MAPPING,
    AMENITY_TAG_MAPPING,
)
from .utils import parse_range_param

# 設定日誌
logger = logging.getLogger(__name__)


class SinyiUrlBuilder:
    """信義房屋URL構建器，根據參數生成搜尋URL"""

    @staticmethod
    def build_url(params: Dict[str, Any], query: str) -> str:
        """
        根據解析的參數構建信義房屋搜尋URL

        Args:
            params: 解析的參數字典
            query: 原始查詢文本，用於輔助判斷

        Returns:
            str: 生成的搜尋URL
        """
        logger.info(f"開始構建URL，參數數量: {len(params)}")
        url_parts = []

        # 處理價格範圍
        if "價格範圍" in params:
            price_param = SinyiUrlBuilder._build_price_param(params["價格範圍"])
            if price_param:
                url_parts.append(price_param)
                logger.debug(f"添加價格參數: {price_param}")

        # 處理房屋類型
        house_types = params.get("房屋類型", [])
        if house_types:
            type_param = SinyiUrlBuilder._build_type_param(house_types)
            if type_param:
                url_parts.append(type_param)
                logger.debug(f"添加房屋類型參數: {type_param}")

        # 處理車位
        if params.get("車位") == "有車位":
            url_parts.append(
                "plane-auto-mix-mechanical-firstfloor-tower-other-yesparking"
            )
            logger.debug("添加有車位參數")
        elif params.get("車位") == "無車位":
            url_parts.append("noparking")
            logger.debug("添加無車位參數")

        # 處理坪數範圍
        if "坪數範圍" in params:
            area_param = parse_range_param(params["坪數範圍"], "area")
            if area_param:
                url_parts.append(area_param)
                logger.debug(f"添加坪數參數: {area_param}")

        # 處理屋齡
        if "屋齡" in params:
            year_param = parse_range_param(params["屋齡"], "year")
            if year_param:
                url_parts.append(year_param)
                logger.debug(f"添加屋齡參數: {year_param}")

        # 處理房間數
        if "房間數" in params:
            room_param = parse_range_param(params["房間數"], "room")
            if room_param:
                url_parts.append(room_param)
                logger.debug(f"添加房間數參數: {room_param}")

        # 排除4樓
        if params.get("排除4樓", False) or "排除4樓" in params:
            url_parts.append("4f-exclude")
            logger.debug("添加排除4樓參數")

        # 處理標籤
        tags = SinyiUrlBuilder._extract_tags(params, query)
        if tags:
            tag_param = "-".join(tags) + "-tags"
            url_parts.append(tag_param)
            logger.debug(f"添加標籤參數: {tag_param}, 標籤數量: {len(tags)}")

        # 處理關鍵字搜尋
        keyword_param = SinyiUrlBuilder._build_keyword_param(params, query, tags)
        if keyword_param:
            url_parts.append(keyword_param)
            logger.debug(f"添加關鍵字參數: {keyword_param}")

        # 處理樓層
        if "樓層" in params:
            floor_param = parse_range_param(params["樓層"], "floor")
            if floor_param:
                url_parts.append(floor_param)
                logger.debug(f"添加樓層參數: {floor_param}")

        # 城市 (必須項目)
        city_code = CITY_MAPPING.get(params.get("城市", "新北市"), "NewTaipei-city")
        url_parts.append(city_code)
        logger.debug(f"添加城市參數: {city_code}")

        # 行政區(郵遞區號)
        if "行政區" in params:
            district = params["行政區"]
            zip_code = DISTRICT_ZIP_MAPPING.get(district, "")
            if zip_code:
                url_parts.append(f"{zip_code}-zip")
                logger.debug(f"添加行政區參數: {zip_code}-zip")

        # 固定排序和頁碼
        url_parts.append("default-desc")
        url_parts.append("1")  # 第一頁

        final_url = f"{SINYI_BASE_URL}/{'/'.join(url_parts)}"
        logger.info(f"URL構建完成: {final_url}")
        return final_url

    @staticmethod
    def _build_price_param(price_range) -> str:
        """構建價格參數"""
        if isinstance(price_range, str):
            if "以上" in price_range:
                num = re.search(r"\d+", price_range)
                if num:
                    return f"{num.group(0)}-up-price"
            elif "以下" in price_range:
                num = re.search(r"\d+", price_range)
                if num:
                    return f"{num.group(0)}-down-price"
            else:
                # 檢查範圍格式 (例如 200-400)
                range_match = re.search(r"(\d+)[-~到至](\d+)", price_range)
                if range_match:
                    return f"{range_match.group(1)}-{range_match.group(2)}-price"
        return ""

    @staticmethod
    def _build_type_param(house_types) -> str:
        """構建房屋類型參數"""
        if isinstance(house_types, list):
            type_codes = [
                TYPE_MAPPING.get(t, "") for t in house_types if t in TYPE_MAPPING
            ]
            if type_codes:
                return "-".join(type_codes) + "-type"
        return ""

    @staticmethod
    def _extract_tags(params: Dict[str, Any], query: str) -> List[str]:
        """提取並構建標籤列表"""
        tags = []

        # 檢查已知的設施標籤
        for tag_name, tag_code in AMENITY_TAG_MAPPING.items():
            tag_found = False
            # 檢查標籤是否在設施標籤列表中
            if "設施標籤" in params and isinstance(params["設施標籤"], list):
                for tag in params["設施標籤"]:
                    if tag_name in tag or tag in tag_name:
                        tag_found = True
                        break
            # 檢查標籤是否直接作為參數存在
            elif tag_name in params or any(tag_name in key for key in params.keys()):
                tag_found = True

            # 為特定標籤進行額外檢查
            if not tag_found:
                if tag_name == "近捷運站" and (
                    "捷運" in query or "MRT" in query.upper()
                ):
                    tag_found = True
                elif tag_name == "有游泳池" and "游泳池" in query:
                    tag_found = True
                elif tag_name == "有健身房" and "健身" in query:
                    tag_found = True

            if tag_found:
                tags.append(tag_code)

        return tags

    @staticmethod
    def _build_keyword_param(
        params: Dict[str, Any], query: str, tags: List[str]
    ) -> str:
        """構建關鍵字參數"""
        # 如果有捷運關鍵字但沒有近捷運站標籤，添加關鍵字搜尋
        if "捷運" in query and "17" not in tags:
            # 如果有具體的捷運站名稱，使用它作為關鍵字
            station_match = re.search(r"捷運(\w+站|\w+線)", query)
            if station_match:
                keyword = station_match.group(0)
                return f"{keyword}-keyword"
            else:
                return "捷運-keyword"
        elif "關鍵字" in params:
            return f"{params['關鍵字']}-keyword"
        return ""
