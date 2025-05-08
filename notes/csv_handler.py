import pandas as pd
import os

def transform_real_estate_csv(input_file, output_file):
    """
    轉換房產交易CSV文件，重新命名欄位並調整欄位順序。
    
    Args:
        input_file: 輸入CSV文件路徑
        output_file: 輸出CSV文件路徑
    """
    print(f"處理文件: {input_file}")
    
    # 讀取CSV文件
    df = pd.read_csv(input_file, encoding='utf-8')
    
    # 欄位重命名映射
    rename_mapping = {
        '土地位置建物門牌': '地址',
        '土地移轉總面積平方公尺': '土地面積平方公尺',
        '建物移轉總面積平方公尺': '建物面積平方公尺',
        '建物現況格局-房': '格局-房',
        '建物現況格局-廳': '格局-廳',
        '建物現況格局-衛': '格局-衛',
        '建物現況格局-隔間': '格局-隔間',
        '總價元': '總價',
        '車位移轉總面積(平方公尺)': '車位面積平方公尺',
        '車位總價元': '車位總價'
    }
    
    # 欄位重命名
    df = df.rename(columns=rename_mapping)
    
    # 需要保留的欄位列表（按照所需順序排列）
    columns_to_keep = [
        '縣市',                 # 先放地理位置相關
        '鄉鎮市區',
        '地址',
        '交易年月日',            # 時間相關
        '交易類別',
        '交易筆棟數',
        '總價',                 # 價格相關
        '單價元平方公尺',
        '每坪單價',
        '建物型態',             # 建物特性相關
        '主要用途',
        '主要建材',
        '建築完成年月',
        '總樓層數',
        '移轉層次',
        '電梯',
        '屋齡',
        '有無管理組織',
        '土地面積平方公尺',      # 面積相關
        '建物面積平方公尺',
        '建物移轉總坪數',
        '主建物面積',
        '附屬建物面積',
        '陽台面積',
        '格局-房',              # 格局相關
        '格局-廳',
        '格局-衛',
        '格局-隔間',
        '車位類別',             # 車位相關
        '車位面積平方公尺',
        '車位總價'
    ]
    
    # 檢查所有欄位是否都存在於原始資料中
    for col in columns_to_keep:
        if col not in df.columns:
            print(f"警告: 欄位 '{col}' 不在原始資料中")
    
    # 只保留所需欄位並按指定順序排列
    # 使用交集操作確保即使原始資料缺少某些欄位也不會出錯
    available_columns = [col for col in columns_to_keep if col in df.columns]
    df = df[available_columns]
    
    # 儲存處理後的檔案
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"處理完成，已儲存至: {output_file}")
    
    return df

def process_all_files():
    """處理所有指定的CSV文件"""
    input_files = ['TP_Sales.csv', 'NTP_Sales.csv']
    output_dir = 'processed'
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    for file in input_files:
        if os.path.exists(file):
            output_file = os.path.join(output_dir, f"processed_{file}")
            results[file] = transform_real_estate_csv(file, output_file)
        else:
            print(f"錯誤: 找不到檔案 {file}")
    
    return results

if __name__ == "__main__":
    print("開始處理房產交易資料...")
    processed_data = process_all_files()
    print("所有檔案處理完成!")
    
    # 顯示處理後的資料概況
    for file, df in processed_data.items():
        print(f"\n{file} 處理結果:")
        print(f"- 總記錄數: {len(df)}")
        print(f"- 欄位數: {len(df.columns)}")
        print(f"- 欄位: {', '.join(df.columns)}")
