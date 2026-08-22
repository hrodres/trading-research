#!/usr/bin/env python3
"""Fase A.1 - Screening de pares (CORREGIDO): alinea por FECHA, liquidez USDT.

CORRECCION del bug de la 1a version: antes alineaba precios por POSICION
(iloc), lo que daba correlaciones espurias cuando los pares empiezan en
fechas distintas (XRP/DOGE/etc.). Solo BTC/ETH salian bien por coincidencia
de inicio/longitud. Ahora alinea por FECHA (indice temporal). Liquidez en
USDT (volume * close), no volume en base (no comparable).
"""
import pandas as pd
import numpy as np
import os

DATADIR = "/freqtrade/user_data/data/coinbase"
PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT",
         "DOGE/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT"]

closes = {}
usdt_vol = {}
for p in PAIRS:
    f = os.path.join(DATADIR, p.replace("/", "_") + "-2h.feather")
    if not os.path.exists(f):
        print("  FALTA", f)
        continue
    df = pd.read_feather(f)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    closes[p] = df["close"]
    usdt_vol[p] = df["volume"] * df["close"]

prices = pd.DataFrame(closes).sort_index()
print("Rango total:", prices.index.min(), "->", prices.index.max())
for p in prices.columns:
    s = prices[p].dropna()
    print(f"  {p:12}: {len(s)} velas, inicio {s.index.min()}")

common = prices.dropna(how="any")
print("\nPeriodo comun:", common.index.min(), "->", common.index.max(), "(", len(common), "velas)")
rets = np.log(common / common.shift(1)).dropna()
liq = {p: usdt_vol[p].reindex(common.index).dropna().median() for p in usdt_vol}

print("\n=== MATRIZ DE CORRELACION (log-returns, periodo comun) ===")
print(rets.corr().round(2).to_string())

print("\n=== LIQUIDEZ (mediana USDT / vela 2h) ===")
for p, v in sorted(liq.items(), key=lambda x: -x[1]):
    print(f"  {p:12}: ${v:,.0f}")

print("\n=== REDUNDANCIA (corr>=0.80) ===")
corr = rets.corr()
high = [(corr.columns[i], corr.columns[j], corr.iloc[i, j])
        for i in range(len(corr.columns))
        for j in range(i + 1, len(corr.columns))
        if corr.iloc[i, j] >= 0.80]
for a, b, c in high:
    print(f"  {a} <-> {b}: {c}")
print(f"({len(high)} redundantes de {len(corr.columns)})")
