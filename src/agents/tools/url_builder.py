import re
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SINYI_BASE_URL = "https://www.sinyi.com.tw/buy/list"

# City mapping
CITY_MAPPING = {
    "台北": "Taipei-city",
    "台北市": "Taipei-city",
    "新北": "NewTaipei-city",
    "新北市": "NewTaipei-city",
}

# District zip mapping
DISTRICT_ZIP_MAPPING = {
    # 台北市
    "中正區": "100",
    "大同區": "103",
    "中山區": "104",
    "松山區": "105",
    "大安區": "106",
    "萬華區": "108",
    "信義區": "110",
    "士林區": "111",
    "北投區": "112",
    "內湖區": "114",
    "南港區": "115",
    "文山區": "116",
    # 新北市
    "萬里區": "207",
    "金山區": "208",
    "板橋區": "220",
    "汐止區": "221",
    "深坑區": "222",
    "石碇區": "223",
    "瑞芳區": "224",
    "平溪區": "226",
    "雙溪區": "227",
    "貢寮區": "228",
    "新店區": "231",
    "坪林區": "232",
    "烏來區": "233",
    "永和區": "234",
    "中和區": "235",
    "土城區": "236",
    "三峽區": "237",
    "樹林區": "238",
    "鶯歌區": "239",
    "三重區": "241",
    "新莊區": "242",
    "泰山區": "243",
    "林口區": "244",
    "蘆洲區": "247",
    "五股區": "248",
    "八里區": "249",
    "淡水區": "251",
    "三芝區": "252",
    "石門區": "253",
}

# Property type mapping
TYPE_MAPPING = {
    "公寓": "apartment",
    "大樓": "dalou",
    "套房": "flat",
    "別墅": "townhouse-villa",
    "透天": "townhouse-villa",
    "辦公": "office",
}

# Amenity tag mapping
AMENITY_TAG_MAPPING = {
    "近學校": "16",
    "近公園": "19",
    "有游泳池": "9",
    "有健身房": "8",
    "近捷運站": "17",
    "近市場": "18",
    "有陽台": "4",
    "有警衛管理": "12",
}


def build_url(params: Dict[str, Any], query: str) -> str:
    """
    Build a Sinyi Real Estate search URL based on parsed parameters.

    Args:
        params: Dictionary of parsed parameters
        query: Original query text for additional context

    Returns:
        str: Generated search URL
    """
    logger.info(f"Building URL, parameter count: {len(params)}")
    url_parts = []

    # Handle price range
    if "價格範圍" in params:
        price_param = _build_price_param(params["價格範圍"])
        if price_param:
            url_parts.append(price_param)
            logger.debug(f"Added price parameter: {price_param}")

    # Handle property type
    house_types = params.get("房屋類型", [])
    if house_types:
        type_param = _build_type_param(house_types)
        if type_param:
            url_parts.append(type_param)
            logger.debug(f"Added property type parameter: {type_param}")

    # Handle parking
    if params.get("車位") == "有車位":
        url_parts.append("plane-auto-mix-mechanical-firstfloor-tower-other-yesparking")
        logger.debug("Added parking parameter")
    elif params.get("車位") == "無車位":
        url_parts.append("noparking")
        logger.debug("Added no-parking parameter")

    # Handle area range
    if "坪數範圍" in params:
        area_param = parse_range_param(params["坪數範圍"], "area")
        if area_param:
            url_parts.append(area_param)
            logger.debug(f"Added area parameter: {area_param}")

    # Handle property age
    if "屋齡" in params:
        year_param = parse_range_param(params["屋齡"], "year")
        if year_param:
            url_parts.append(year_param)
            logger.debug(f"Added property age parameter: {year_param}")

    # Handle room count
    if "房間數" in params:
        room_param = parse_range_param(params["房間數"], "room")
        if room_param:
            url_parts.append(room_param)
            logger.debug(f"Added room count parameter: {room_param}")

    # Handle 4th floor exclusion
    if params.get("排除4樓", False) or "排除4樓" in params:
        url_parts.append("4f-exclude")
        logger.debug("Added 4th floor exclusion parameter")

    # Handle amenity tags
    tags = _extract_tags(params, query)
    if tags:
        tag_param = "-".join(tags) + "-tags"
        url_parts.append(tag_param)
        logger.debug(f"Added tag parameter: {tag_param}, tag count: {len(tags)}")

    # Handle keyword search
    keyword_param = _build_keyword_param(params, query, tags)
    if keyword_param:
        url_parts.append(keyword_param)
        logger.debug(f"Added keyword parameter: {keyword_param}")

    # Handle floor
    if "樓層" in params:
        floor_param = parse_range_param(params["樓層"], "floor")
        if floor_param:
            url_parts.append(floor_param)
            logger.debug(f"Added floor parameter: {floor_param}")

    # City (required parameter)
    city_code = CITY_MAPPING.get(params.get("城市", "新北市"), "NewTaipei-city")
    url_parts.append(city_code)
    logger.debug(f"Added city parameter: {city_code}")

    # District (zip code)
    if "行政區" in params:
        district = params["行政區"]
        zip_code = DISTRICT_ZIP_MAPPING.get(district, "")
        if zip_code:
            url_parts.append(f"{zip_code}-zip")
            logger.debug(f"Added district parameter: {zip_code}-zip")

    # Fixed sorting and page
    url_parts.append("default-desc")  # Default sorting
    url_parts.append("1")  # First page

    final_url = f"{SINYI_BASE_URL}/{'/'.join(url_parts)}"
    logger.info(f"URL building completed: {final_url}")
    return final_url


def _build_price_param(price_range) -> str:
    """Build price parameter"""
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
            # Check range format (e.g., 200-400)
            range_match = re.search(r"(\d+)[-~到至](\d+)", price_range)
            if range_match:
                return f"{range_match.group(1)}-{range_match.group(2)}-price"
    return ""


def _build_type_param(house_types) -> str:
    """Build property type parameter"""
    if isinstance(house_types, list):
        type_codes = [TYPE_MAPPING.get(t, "") for t in house_types if t in TYPE_MAPPING]
        if type_codes:
            return "-".join(type_codes) + "-type"
    return ""


def _extract_tags(params: Dict[str, Any], query: str) -> List[str]:
    """Extract and build tag list"""
    tags = []

    # Check for known amenity tags
    for tag_name, tag_code in AMENITY_TAG_MAPPING.items():
        tag_found = False
        # Check if tag is in amenity tag list
        if "設施標籤" in params and isinstance(params["設施標籤"], list):
            for tag in params["設施標籤"]:
                if tag_name in tag or tag in tag_name:
                    tag_found = True
                    break
        # Check if tag exists directly as a parameter
        elif tag_name in params or any(tag_name in key for key in params.keys()):
            tag_found = True

        # Additional checks for specific tags
        if not tag_found:
            if tag_name == "近捷運站" and ("捷運" in query or "MRT" in query.upper()):
                tag_found = True
            elif tag_name == "有游泳池" and "游泳池" in query:
                tag_found = True
            elif tag_name == "有健身房" and "健身" in query:
                tag_found = True

        if tag_found:
            tags.append(tag_code)

    return tags


def _build_keyword_param(params: Dict[str, Any], query: str, tags: List[str]) -> str:
    """Build keyword parameter"""
    # If MRT keyword exists but no MRT station tag, add keyword search
    if "捷運" in query and "17" not in tags:
        # If there's a specific station name, use it as keyword
        station_match = re.search(r"捷運(\w+站|\w+線)", query)
        if station_match:
            keyword = station_match.group(0)
            return f"{keyword}-keyword"
        else:
            return "捷運-keyword"
    elif "關鍵字" in params:
        return f"{params['關鍵字']}-keyword"
    return ""


def parse_range_param(value, suffix: str) -> str:
    """
    Parse range parameters and convert to URL format

    Args:
        value: Value to parse
        suffix: URL parameter suffix

    Returns:
        str: Formatted URL parameter

    Examples:
        "10坪以上" -> "10-up-area"
        "5-10年" -> "5-10-year"
    """
    if not value:
        return ""

    # Log the process
    logger.debug(f"Parsing range parameter: {value}, suffix: {suffix}")

    # Convert to string
    if not isinstance(value, str):
        value = str(value)

    # Check for "以上" or "以下" (above/below)
    if "以上" in value:
        num = re.search(r"\d+", value)
        if num:
            result = f"{num.group(0)}-up-{suffix}"
            logger.debug(f"Parsed as 'above' range: {result}")
            return result
    elif "以下" in value:
        num = re.search(r"\d+", value)
        if num:
            result = f"{num.group(0)}-down-{suffix}"
            logger.debug(f"Parsed as 'below' range: {result}")
            return result

    # Check for range format
    range_match = re.search(r"(\d+)[-~到至](\d+)", value)
    if range_match:
        result = f"{range_match.group(1)}-{range_match.group(2)}-{suffix}"
        logger.debug(f"Parsed as range value: {result}")
        return result

    # If only a number, check if it's a single value
    num_match = re.search(r"^\d+$", value.strip())
    if num_match:
        if suffix == "room":  # Special handling for room count
            result = f"1-{value.strip()}-{suffix}"
            logger.debug(f"Parsed as room count range: {result}")
            return result
        else:
            result = f"{value.strip()}-up-{suffix}"
            logger.debug(f"Parsed as default 'above' range: {result}")
            return result

    logger.debug(f"Could not parse range parameter: {value}")
    return ""


def generate_search_explanation(params: Dict[str, Any]) -> str:
    """
    Generate human-readable search explanation based on parsed parameters

    Args:
        params: Dictionary of parsed parameters

    Returns:
        str: Human-readable search explanation
    """
    parts = []

    if "城市" in params:
        parts.append(params["城市"])

    if "行政區" in params:
        parts.append(params["行政區"])

    if "房屋類型" in params:
        if isinstance(params["房屋類型"], list):
            parts.append("、".join(params["房屋類型"]))
        else:
            parts.append(str(params["房屋類型"]))

    if "設施標籤" in params:
        if isinstance(params["設施標籤"], list):
            parts.append("、".join(params["設施標籤"]))
        else:
            parts.append(str(params["設施標籤"]))

    if "關鍵字" in params:
        parts.append(f"keyword '{params['關鍵字']}'")

    if "價格範圍" in params:
        parts.append(f"price {params['價格範圍']}")

    if "坪數範圍" in params:
        parts.append(f"area {params['坪數範圍']}")

    if "排除4樓" in params and params["排除4樓"]:
        parts.append("excluding 4th floor")

    if "車位" in params:
        parts.append(params["車位"])

    if parts:
        return "Search: " + ", ".join(parts)
    else:
        return "Search all properties"


def map_llm_params_to_internal(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map LLM output parameters to internal parameter format

    Args:
        params: LLM output parameter dictionary

    Returns:
        Dict: Converted internal parameter dictionary
    """
    logger.debug(f"Mapping LLM parameters to internal format: {params}")

    # Deep copy to avoid modifying original data
    import copy

    result = copy.deepcopy(params)

    # Field mappings
    field_mappings = {
        "city": "城市",
        "district": "行政區",
        "property_type": "房屋類型",
        "price_range": "價格範圍",
        "area_range": "坪數範圍",
        "rooms": "房間數",
        "floor": "樓層",
        "year": "屋齡",
        "amenities": "設施標籤",
        "keyword": "關鍵字",
    }

    # Perform conversion
    for eng_field, ch_field in field_mappings.items():
        if eng_field in result:
            # Special handling for property type field, ensure it's a list
            if eng_field == "property_type":
                value = result.pop(eng_field)
                if isinstance(value, list):
                    result[ch_field] = value
                else:
                    result[ch_field] = [value]
            else:
                result[ch_field] = result.pop(eng_field)

    # Special handling for special conditions
    if "special_conditions" in result:
        conditions = result.pop("special_conditions")
        if isinstance(conditions, list):
            for condition in conditions:
                _process_special_condition(result, condition)
        else:
            _process_special_condition(result, conditions)

    logger.debug(f"Mapped internal parameters: {result}")
    return result


def _process_special_condition(params: Dict[str, Any], condition: str):
    """Process special conditions"""
    if "有車位" in condition:
        params["車位"] = "有車位"
    elif "無車位" in condition:
        params["車位"] = "無車位"
    elif "排除4樓" in condition or "不要4樓" in condition:
        params["排除4樓"] = True
