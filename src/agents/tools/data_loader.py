# agents/tools/data_loader.py
import pandas as pd
import time
import psutil
from typing import Optional, Dict
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CACHE_EXPIRY_SECONDS = 3600  # 1 hour cache expiry

# Global data cache
_DATA_CACHE = {
    "台北市": None,
    "新北市": None,
    "all": None,
    "last_loaded": {"台北市": None, "新北市": None, "all": None},
}

# Cache control flag
_CACHE_ENABLED = False  # Default to disabled


def enable_cache(enabled: bool = True) -> None:
    """Enable or disable memory caching."""
    global _CACHE_ENABLED
    old_state = _CACHE_ENABLED
    _CACHE_ENABLED = enabled
    logger.info(f"Cache state changed: {old_state} -> {enabled}")

    # Optionally clear cache if disabling
    if not enabled:
        clear_cache()


def is_cache_enabled() -> bool:
    """Return current cache state."""
    global _CACHE_ENABLED
    return _CACHE_ENABLED


def load_city_data(city: Optional[str] = None) -> pd.DataFrame:
    """Load real estate data. If city is specified, load data for that city, otherwise load all data."""
    global _DATA_CACHE, _CACHE_ENABLED

    # Determine cache key
    cache_key = (
        "台北市"
        if city and ("台北" in city or "臺北" in city)
        else "新北市" if city and "新北" in city else "all"
    )

    # Check if cache is enabled and valid
    now = time.time()
    if (
        _CACHE_ENABLED
        and _DATA_CACHE[cache_key] is not None
        and _DATA_CACHE["last_loaded"][cache_key] is not None
        and now - _DATA_CACHE["last_loaded"][cache_key] < CACHE_EXPIRY_SECONDS
    ):
        logger.info(
            f"Using cached {cache_key} data, cache age: {int(now - _DATA_CACHE['last_loaded'][cache_key])}s"
        )
        return _DATA_CACHE[cache_key]

    # Reload data if cache is invalid or disabled
    start_time = time.time()
    base_path = Path(__file__).parent.parent.parent / "data"

    # Get memory usage before loading
    mem_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    # Specify data types to avoid mixed type warnings
    dtypes = {"鄉鎮市區": str, "交易標的": str, "建物型態": str}

    if city and ("台北" in city or "臺北" in city):
        file_path = base_path / "TP_Sales.csv"
        logger.info(f"Loading Taipei data: {file_path}")
        df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)

        # Get memory usage after loading
        mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        load_time = time.time() - start_time

        # Update cache if enabled
        if _CACHE_ENABLED:
            _DATA_CACHE["台北市"] = df
            _DATA_CACHE["last_loaded"]["台北市"] = now
            logger.info("Taipei data added to cache")

        # Log loading info
        logger.info(f"Taipei data loaded, {len(df)} records")
        logger.info(f"Loading time: {load_time:.2f}s")
        logger.info(
            f"Memory usage: +{(mem_after - mem_before):.2f}MB, total {mem_after:.2f}MB"
        )

        return df

    elif city and "新北" in city:
        file_path = base_path / "NTP_Sales.csv"
        logger.info(f"Loading New Taipei data: {file_path}")
        df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)

        # Get memory usage after loading
        mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        load_time = time.time() - start_time

        # Update cache if enabled
        if _CACHE_ENABLED:
            _DATA_CACHE["新北市"] = df
            _DATA_CACHE["last_loaded"]["新北市"] = now
            logger.info("New Taipei data added to cache")

        # Log loading info
        logger.info(f"New Taipei data loaded, {len(df)} records")
        logger.info(f"Loading time: {load_time:.2f}s")
        logger.info(
            f"Memory usage: +{(mem_after - mem_before):.2f}MB, total {mem_after:.2f}MB"
        )

        return df

    else:
        # Try using cached city data
        if (
            _CACHE_ENABLED
            and _DATA_CACHE["台北市"] is not None
            and _DATA_CACHE["新北市"] is not None
            and _DATA_CACHE["last_loaded"]["台北市"] is not None
            and _DATA_CACHE["last_loaded"]["新北市"] is not None
            and now - _DATA_CACHE["last_loaded"]["台北市"] < CACHE_EXPIRY_SECONDS
            and now - _DATA_CACHE["last_loaded"]["新北市"] < CACHE_EXPIRY_SECONDS
        ):
            logger.info("Using cached Taipei and New Taipei data for merging")
            merge_start = time.time()
            df = pd.concat(
                [_DATA_CACHE["台北市"], _DATA_CACHE["新北市"]], ignore_index=True
            )
            merge_time = time.time() - merge_start

            # Update merged data cache
            _DATA_CACHE["all"] = df
            _DATA_CACHE["last_loaded"]["all"] = now

            logger.info(f"Merged cached data, time: {merge_time:.2f}s")
            return df

        # Load both cities' data and merge
        tp_file_path = base_path / "TP_Sales.csv"
        ntp_file_path = base_path / "NTP_Sales.csv"

        logger.info(f"Loading Taipei data: {tp_file_path}")
        tp_load_start = time.time()
        tp_df = pd.read_csv(tp_file_path, dtype=dtypes, low_memory=False)
        tp_load_time = time.time() - tp_load_start
        logger.info(
            f"Taipei data loaded, {len(tp_df)} records, time: {tp_load_time:.2f}s"
        )

        # Update Taipei cache if enabled
        if _CACHE_ENABLED:
            _DATA_CACHE["台北市"] = tp_df
            _DATA_CACHE["last_loaded"]["台北市"] = now

        logger.info(f"Loading New Taipei data: {ntp_file_path}")
        ntp_load_start = time.time()
        ntp_df = pd.read_csv(ntp_file_path, dtype=dtypes, low_memory=False)
        ntp_load_time = time.time() - ntp_load_start
        logger.info(
            f"New Taipei data loaded, {len(ntp_df)} records, time: {ntp_load_time:.2f}s"
        )

        # Update New Taipei cache if enabled
        if _CACHE_ENABLED:
            _DATA_CACHE["新北市"] = ntp_df
            _DATA_CACHE["last_loaded"]["新北市"] = now

        # Merge data
        merge_start = time.time()
        df = pd.concat([tp_df, ntp_df], ignore_index=True)
        merge_time = time.time() - merge_start

        # Get memory usage after loading
        mem_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        total_load_time = time.time() - start_time

        # Update all data cache if enabled
        if _CACHE_ENABLED:
            _DATA_CACHE["all"] = df
            _DATA_CACHE["last_loaded"]["all"] = now
            logger.info("Merged data added to cache")

        # Log merging info
        logger.info(
            f"Data merging complete, {len(df)} records, merge time: {merge_time:.2f}s"
        )
        logger.info(f"Total loading time: {total_load_time:.2f}s")
        logger.info(
            f"Memory usage: +{(mem_after - mem_before):.2f}MB, total {mem_after:.2f}MB"
        )

        return df


def clear_cache(city: Optional[str] = None):
    """Clear the data cache for a specific city or all cities."""
    global _DATA_CACHE

    if city is None:
        # Clear all caches
        for key in _DATA_CACHE:
            if key != "last_loaded":
                _DATA_CACHE[key] = None
        for key in _DATA_CACHE["last_loaded"]:
            _DATA_CACHE["last_loaded"][key] = None
        logger.info("All data caches cleared")
    else:
        # Clear specific city cache
        cache_key = (
            "台北市"
            if "台北" in city or "臺北" in city
            else "新北市" if "新北" in city else None
        )
        if cache_key and cache_key in _DATA_CACHE:
            _DATA_CACHE[cache_key] = None
            _DATA_CACHE["last_loaded"][cache_key] = None
            # Also clear all data cache since it depends on city data
            _DATA_CACHE["all"] = None
            _DATA_CACHE["last_loaded"]["all"] = None
            logger.info(f"{cache_key} data cache cleared")


def get_cache_status() -> Dict:
    """Get current cache status information."""
    global _DATA_CACHE, _CACHE_ENABLED

    now = time.time()
    status = {
        "enabled": _CACHE_ENABLED,
        "cache_entries": {},
    }

    for key in ["台北市", "新北市", "all"]:
        if _DATA_CACHE[key] is not None and _DATA_CACHE["last_loaded"][key] is not None:
            status["cache_entries"][key] = {
                "record_count": len(_DATA_CACHE[key]),
                "age_seconds": int(now - _DATA_CACHE["last_loaded"][key]),
                "is_valid": (
                    now - _DATA_CACHE["last_loaded"][key] < CACHE_EXPIRY_SECONDS
                ),
                "memory_usage_mb": _DATA_CACHE[key].memory_usage(deep=True).sum()
                / 1024
                / 1024,
            }
        else:
            status["cache_entries"][key] = {
                "record_count": 0,
                "age_seconds": None,
                "is_valid": False,
                "memory_usage_mb": 0,
            }

    return status
