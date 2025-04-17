# AI_agent/data_loader.py
import pandas as pd
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """數據加載器，負責加載房地產數據。"""
    
    @staticmethod
    def load_city_data(city: Optional[str] = None) -> pd.DataFrame:
        """載入房地產資料。如果指定城市，則載入該城市資料，否則載入所有資料。"""
        logger.info(f"開始載入城市數據: {city}")
        base_path = Path(__file__).parent.parent / "data"
        
        # 指定數據類型以避免混合類型警告
        dtypes = {
            '鄉鎮市區': str,
            '交易標的': str,
            '建物型態': str
        }
        
        if city and ('台北' in city or '臺北' in city):
            file_path = base_path / "TP_Sales.csv"
            logger.info(f"載入台北市數據: {file_path}")
            df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)
            logger.info(f"台北市數據載入完成，共 {len(df)} 筆記錄")
            return df
        elif city and '新北' in city:
            file_path = base_path / "NTP_Sales.csv"
            logger.info(f"載入新北市數據: {file_path}")
            df = pd.read_csv(file_path, dtype=dtypes, low_memory=False)
            logger.info(f"新北市數據載入完成，共 {len(df)} 筆記錄")
            return df
        else:
            # 載入兩個城市的資料並合併
            tp_file_path = base_path / "TP_Sales.csv"
            ntp_file_path = base_path / "NTP_Sales.csv"
            
            logger.info(f"載入台北市數據: {tp_file_path}")
            tp_df = pd.read_csv(tp_file_path, dtype=dtypes, low_memory=False)
            logger.info(f"台北市數據載入完成，共 {len(tp_df)} 筆記錄")
            
            logger.info(f"載入新北市數據: {ntp_file_path}")
            ntp_df = pd.read_csv(ntp_file_path, dtype=dtypes, low_memory=False)
            logger.info(f"新北市數據載入完成，共 {len(ntp_df)} 筆記錄")
            
            # 合併數據
            df = pd.concat([tp_df, ntp_df], ignore_index=True)
            logger.info(f"合併數據完成，共 {len(df)} 筆記錄")
            return df