"""에너지 가격 더미 CSV 생성 스크립트 (P5 캡처용)

94행(2018-01 ~ 2025-10), 12컬럼, seed=42 재현 가능.
brent_oil_price → SHAP 1위, jkm_spot_price → SHAP 2위 보장.
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

N = 94  # 2018-01 ~ 2025-10
dates = pd.date_range("2018-01", periods=N, freq="MS")

# --- 독립 변수 ---

# 브렌트유: random walk (50~90 범위)
brent = np.cumsum(np.random.normal(0, 2.5, N)) + 65
brent = np.clip(brent, 40, 110)

# JKM 현물가격: 브렌트유와 상관 0.65 + 독립 노이즈
jkm = brent * 0.25 + np.cumsum(np.random.normal(0, 1.2, N)) + 8
jkm = np.clip(jkm, 5, 50)

# 환율 (KRW/USD): 트렌드 + 노이즈
exchange = np.linspace(1080, 1350, N) + np.random.normal(0, 30, N)

# PPI (생산자물가지수): 완만한 상승
ppi = np.linspace(100, 115, N) + np.random.normal(0, 1.5, N)

# 난방도일: 계절성 (겨울 높고 여름 낮음)
months = np.array([d.month for d in dates])
heating = 300 * np.maximum(0, np.cos((months - 1) / 12 * 2 * np.pi)) + np.random.normal(0, 20, N)
heating = np.clip(heating, 0, 500)

# LNG 수입량 (천톤): 계절성 + 트렌드
lng_import = 3000 + 500 * np.cos((months - 1) / 12 * 2 * np.pi) + np.linspace(0, 400, N) + np.random.normal(0, 100, N)

# 천연가스 재고 (백만톤)
gas_inventory = 8 + np.random.normal(0, 1.2, N)
gas_inventory = np.clip(gas_inventory, 3, 15)

# 산업용 전력 소비 (GWh)
power_consumption = 25000 + 2000 * np.cos((months - 7) / 12 * 2 * np.pi) + np.random.normal(0, 500, N)

# CPI (소비자물가지수)
cpi = np.linspace(100, 112, N) + np.random.normal(0, 0.8, N)

# 수입 LNG 단가 ($/MMBTU)
lng_price = jkm * 0.8 + np.random.normal(0, 1.5, N) + 3
lng_price = np.clip(lng_price, 5, 45)

# 원유 수입량 (천배럴)
crude_import = 80000 + np.random.normal(0, 5000, N)

# --- 타겟: 국내 가스 도입 원가 (원/MJ) ---
# 가중 합산: brent(0.35) + jkm(0.25) + exchange(0.10) + ppi(0.08) + heating(0.07) + lng(0.05)
target = (
    0.35 * (brent - brent.mean()) / brent.std()
    + 0.25 * (jkm - jkm.mean()) / jkm.std()
    + 0.10 * (exchange - exchange.mean()) / exchange.std()
    + 0.08 * (ppi - ppi.mean()) / ppi.std()
    + 0.07 * (heating - heating.mean()) / heating.std()
    + 0.05 * (lng_import - lng_import.mean()) / lng_import.std()
    + np.random.normal(0, 0.15, N)
)
# 스케일링: 실제 가스 도입 원가 범위 (15~35 원/MJ)
target = 25 + target * 4
target = np.round(target, 2)

# --- DataFrame 조립 ---
df = pd.DataFrame({
    "date": dates.strftime("%Y-%m"),
    "brent_oil_price": np.round(brent, 2),
    "jkm_spot_price": np.round(jkm, 2),
    "exchange_rate_krw": np.round(exchange, 1),
    "ppi_index": np.round(ppi, 2),
    "heating_degree_days": np.round(heating, 1),
    "lng_import_volume": np.round(lng_import, 0).astype(int),
    "gas_inventory": np.round(gas_inventory, 2),
    "power_consumption": np.round(power_consumption, 0).astype(int),
    "cpi_index": np.round(cpi, 2),
    "lng_import_price": np.round(lng_price, 2),
    "domestic_gas_price": target,
})

# --- 저장 ---
out_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "energy_price_sample.csv"
df.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"Generated: {out_path}")
print(f"Shape: {df.shape}")
print(f"\nFirst 5 rows:\n{df.head()}")
print(f"\nTarget stats:\n{df['domestic_gas_price'].describe()}")
