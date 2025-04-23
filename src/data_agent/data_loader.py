# AI_agent/data_loader.py
import pandas as pd
import time
import psutil
from typing import Optional, Dict
from pathlib import Path
import logging
from .config import CACHE_EXPIRY_SECONDS

logger = logging.getLogger(__name__)

# 全局數據緩存
_DATA_CACHE = {
    "台北市": None,
    "新北市": None,
    "all": None,
    "last_loaded": {"台北市": None, "新北市": None, "all": None},
}

# 是否啟用內存緩存的控制標誌
_CACHE_ENABLED = False  # 默認禁用緩存


class DataLoader:
    """數據加載器，負責加載房地產數據。"""

    @staticmethod
    def enable_cache(enabled: bool = True) -> None:
        """啟用或禁用內存緩存功能。"""
        global _CACHE_ENABLED
        old_state = _CACHE_ENABLED
        _CACHE_ENABLED = enabled
        logger.info(f"內存緩存狀態變更: {old_state} -> {enabled}")

        # 如果禁用緩存，可以選擇清除現有緩存數據，釋放內存
        if not enabled:
            DataLoader.clear_cache()

    @staticmethod
    def is_cache_enabled() -> bool:
        """返回當前緩存是否啟用的狀態。"""
        global _CACHE_ENABLED
        return _CACHE_ENABLED

    @staticmethod
    def load_city_data(city: Optional[str] = None) -> pd.DataFrame:
        """載入房地產資料。如果指定城市，則載入該城市資料，否則載入所有資料。"""
        global _DATA_CACHE, _CACHE_ENABLED

        # 決定緩存键
        cache_key = (
            "台北市"
            if city and ("台北" in city or "臺北" in city)
            else "新北市" if city and "新北" in city else "all"
        )

        # 檢查緩存是否啟用，以及緩存是否有效（存在且未過期）
        now = time.time()
        if (
            _CACHE_ENABLED
            and _DATA_CACHE[cache_key] is not None
            and _DATA_CACHE["last_loaded"][cache_key] is not None
            and now - _DATA_CACHE["last_loaded"][cache_key] < CACHE_EXPIRY_SECONDS
        ):
            logger.info(
                f"使用緩存的{cache_key}數據，緩存時間: {int(now - _DATA_CACHE['last_loaded'][cache_key])}秒"
            )
            return _DATA_CACHE[cache_key]

        # 如果緩存未啟用或無效，重新加載數據
        start_time = time.time()
        base_path = Path(__file__).parent.parent / "data"

        # 獲取加載前內存使用情況
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # 指定數據類型以避免混合類型警告
        dtypes = {"鄉鎮市區": str, "交易標的": str, "建物型態": str}

        if city and ("台北" in city or "臺北" in city):
            file_path = base_path / "TP_Sales.csv"
            logger.info(f"載入台北市數據: {file_path}")
            df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)

            # 獲取加載後內存使用情況
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            load_time = time.time() - start_time

            # 如果緩存已啟用，更新緩存
            if _CACHE_ENABLED:
                _DATA_CACHE["台北市"] = df
                _DATA_CACHE["last_loaded"]["台北市"] = now
                logger.info("台北市數據已添加到緩存")
            else:
                logger.info("緩存已禁用，不保存數據到緩存")

            # 記錄加載信息
            logger.info(f"台北市數據載入完成，共 {len(df)} 筆記錄")
            logger.info(f"數據加載耗時: {load_time:.2f}秒")
            logger.info(
                f"內存使用: 增加 {(mem_after - mem_before):.2f} MB，總計 {mem_after:.2f} MB"
            )

            return df

        elif city and "新北" in city:
            file_path = base_path / "NTP_Sales.csv"
            logger.info(f"載入新北市數據: {file_path}")
            df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)

            # 獲取加載後內存使用情況
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            load_time = time.time() - start_time

            # 如果緩存已啟用，更新緩存
            if _CACHE_ENABLED:
                _DATA_CACHE["新北市"] = df
                _DATA_CACHE["last_loaded"]["新北市"] = now
                logger.info("新北市數據已添加到緩存")
            else:
                logger.info("緩存已禁用，不保存數據到緩存")

            # 記錄加載信息
            logger.info(f"新北市數據載入完成，共 {len(df)} 筆記錄")
            logger.info(f"數據加載耗時: {load_time:.2f}秒")
            logger.info(
                f"內存使用: 增加 {(mem_after - mem_before):.2f} MB，總計 {mem_after:.2f} MB"
            )

            return df

        else:
            # 檢查是否可以利用已緩存的城市數據（如果緩存已啟用）
            if (
                _CACHE_ENABLED
                and _DATA_CACHE["台北市"] is not None
                and _DATA_CACHE["新北市"] is not None
                and _DATA_CACHE["last_loaded"]["台北市"] is not None
                and _DATA_CACHE["last_loaded"]["新北市"] is not None
                and now - _DATA_CACHE["last_loaded"]["台北市"] < CACHE_EXPIRY_SECONDS
                and now - _DATA_CACHE["last_loaded"]["新北市"] < CACHE_EXPIRY_SECONDS
            ):
                logger.info("使用緩存的台北市和新北市數據合併")
                merge_start = time.time()
                df = pd.concat(
                    [_DATA_CACHE["台北市"], _DATA_CACHE["新北市"]], ignore_index=True
                )
                merge_time = time.time() - merge_start

                # 更新合併數據緩存
                _DATA_CACHE["all"] = df
                _DATA_CACHE["last_loaded"]["all"] = now

                logger.info(f"合併緩存數據完成，耗時: {merge_time:.2f}秒")
                return df

            # 載入兩個城市的資料並合併
            tp_file_path = base_path / "TP_Sales.csv"
            ntp_file_path = base_path / "NTP_Sales.csv"

            logger.info(f"載入台北市數據: {tp_file_path}")
            tp_load_start = time.time()
            tp_df = pd.read_csv(tp_file_path, dtype=dtypes, low_memory=False)
            tp_load_time = time.time() - tp_load_start
            logger.info(
                f"台北市數據載入完成，共 {len(tp_df)} 筆記錄，耗時: {tp_load_time:.2f}秒"
            )

            # 如果緩存已啟用，更新台北市緩存
            if _CACHE_ENABLED:
                _DATA_CACHE["台北市"] = tp_df
                _DATA_CACHE["last_loaded"]["台北市"] = now

            logger.info(f"載入新北市數據: {ntp_file_path}")
            ntp_load_start = time.time()
            ntp_df = pd.read_csv(ntp_file_path, dtype=dtypes, low_memory=False)
            ntp_load_time = time.time() - ntp_load_start
            logger.info(
                f"新北市數據載入完成，共 {len(ntp_df)} 筆記錄，耗時: {ntp_load_time:.2f}秒"
            )

            # 如果緩存已啟用，更新新北市緩存
            if _CACHE_ENABLED:
                _DATA_CACHE["新北市"] = ntp_df
                _DATA_CACHE["last_loaded"]["新北市"] = now

            # 合併數據
            merge_start = time.time()
            df = pd.concat([tp_df, ntp_df], ignore_index=True)
            merge_time = time.time() - merge_start

            # 獲取加載後內存使用情況
            mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            total_load_time = time.time() - start_time

            # 如果緩存已啟用，更新全部數據緩存
            if _CACHE_ENABLED:
                _DATA_CACHE["all"] = df
                _DATA_CACHE["last_loaded"]["all"] = now
                logger.info("合併數據已添加到緩存")
            else:
                logger.info("緩存已禁用，不保存合併數據到緩存")

            # 記錄合併信息
            logger.info(
                f"合併數據完成，共 {len(df)} 筆記錄，合併耗時: {merge_time:.2f}秒"
            )
            logger.info(f"總數據加載耗時: {total_load_time:.2f}秒")
            logger.info(
                f"內存使用: 增加 {(mem_after - mem_before):.2f} MB，總計 {mem_after:.2f} MB"
            )

            return df

    @staticmethod
    def clear_cache(city: Optional[str] = None):
        """清除指定城市或所有城市的數據緩存。"""
        global _DATA_CACHE

        if city is None:
            # 清除所有緩存
            for key in _DATA_CACHE:
                if key != "last_loaded":
                    _DATA_CACHE[key] = None
            for key in _DATA_CACHE["last_loaded"]:
                _DATA_CACHE["last_loaded"][key] = None
            logger.info("已清除所有數據緩存")
        else:
            # 清除指定城市的緩存
            cache_key = (
                "台北市"
                if "台北" in city or "臺北" in city
                else "新北市" if "新北" in city else None
            )
            if cache_key and cache_key in _DATA_CACHE:
                _DATA_CACHE[cache_key] = None
                _DATA_CACHE["last_loaded"][cache_key] = None
                # 同時清除全部數據緩存，因為它依賴於各城市數據
                _DATA_CACHE["all"] = None
                _DATA_CACHE["last_loaded"]["all"] = None
                logger.info(f"已清除{cache_key}數據緩存")

    @staticmethod
    def get_cache_status() -> Dict:
        """獲取當前緩存狀態信息。"""
        global _DATA_CACHE, _CACHE_ENABLED

        now = time.time()
        status = {
            "enabled": _CACHE_ENABLED,  # 添加緩存狀態
        }

        for key in _DATA_CACHE:
            if key != "last_loaded":
                if _DATA_CACHE[key] is not None:
                    last_loaded = _DATA_CACHE["last_loaded"][key]
                    if last_loaded is not None:
                        age_seconds = now - last_loaded
                        status[key] = {
                            "cached": True,
                            "age_seconds": age_seconds,
                            "age_minutes": age_seconds / 60,
                            "size_records": len(_DATA_CACHE[key]),
                            "expired": age_seconds > CACHE_EXPIRY_SECONDS,
                        }
                    else:
                        status[key] = {
                            "cached": True,
                            "age_seconds": None,
                            "expired": True,
                        }
                else:
                    status[key] = {"cached": False}

        return status
