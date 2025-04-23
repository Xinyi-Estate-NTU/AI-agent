"""爬蟲模塊 - 負責抓取和解析房產網站數據"""

import logging
from typing import Dict, Any, List, Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy
import json
import asyncio
from .config import EXTRACT_SCHEMA

# 設定日誌
logger = logging.getLogger(__name__)


class PropertyScraper:
    """房產網站爬蟲，抓取和解析房產數據"""

    def __init__(self, llm):
        """
        初始化爬蟲

        Args:
            llm: 用於分析的語言模型
        """
        self.llm = llm

    async def scrape_property_listings(
        self, url: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        爬取房產列表數據

        Args:
            url: 要爬取的網址

        Returns:
            Optional[List[Dict[str, Any]]]: 爬取到的房產數據列表，如果失敗則返回None
        """
        logger.info(f"開始爬取房產列表: {url}")

        try:
            # Create an XPath extraction strategy with our schema
            extraction_strategy = JsonXPathExtractionStrategy(
                EXTRACT_SCHEMA, verbose=True
            )

            # Configure the crawler
            config = CrawlerRunConfig(
                # Bypass cache to always get fresh data
                cache_mode=CacheMode.BYPASS,
                # Use our extraction strategy
                extraction_strategy=extraction_strategy,
                # Wait for content to load fully
                wait_for="css:.buy-list-item",
            )

            # Use AsyncWebCrawler to scrape the live website
            async with AsyncWebCrawler(verbose=True) as crawler:
                # Extract structured data
                logger.debug("提取結構化數據...")
                result = await crawler.arun(url=url, config=config)

                # Parse and display results
                if result.success:
                    data = json.loads(result.extracted_content)
                    logger.info(f"已提取 {len(data)} 條房產資訊")
                    if data:
                        logger.info(f"已提取 {len(data)} 條房產資訊")
                        logger.info(f"首條資料: {data[0]}")
                    return data
                else:
                    logger.error(f"數據提取失敗: {result.error_message}")
                    return None

        except Exception as e:
            logger.error(f"爬取過程中發生錯誤: {str(e)}")
            import traceback

            logger.debug(f"錯誤詳情: {traceback.format_exc()}")
            return None
