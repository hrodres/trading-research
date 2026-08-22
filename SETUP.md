# SETUP — freqtrade nativo

Los backtests corren con **freqtrade instalado de forma nativa** en un contenedor
LXC dedicado (Proxmox). Entorno autocontenido: `/opt/freqtrade/user_data/`.

## Infra
- Proxmox `pve` (192.168.1.222). CT **113**, Debian 13, 4 cores / 4 GB RAM, 8 GB disco.
- IP 192.168.1.58 (DHCP). Acceso: `pct exec 113 -- ...` desde el host.
- freqtrade 2026.7 en venv `/opt/ft`.

## Instalación reproducible
```bash
pct create 113 local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst \
  --cores 4 --memory 4096 --swap 1024 --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --hostname freqtrade-native --unprivileged 1
pct start 113

pct exec 113 -- bash -c '
apt-get update -y
apt-get install -y python3-venv python3-pip git curl build-essential pkg-config libta-lib-dev
python3 -m venv /opt/ft
/opt/ft/bin/pip install --upgrade pip wheel
/opt/ft/bin/pip install -r requirements.txt
/opt/ft/bin/freqtrade --version
'
pct exec 113 -- mkdir -p /opt/freqtrade/user_data/{data/coinbase,strategies,scripts,configs,results}
```

## Klines
Descargar 9 pares Coinbase 2h a `/opt/freqtrade/user_data/data/coinbase/<PAR>_USDT-2h.feather`.

## Correr un backtest
```bash
pct exec 113 -- bash -c '
cd /opt/freqtrade
/opt/ft/bin/freqtrade backtesting \
  --userdir /opt/freqtrade/user_data --datadir /opt/freqtrade/user_data/data/coinbase \
  --config /opt/freqtrade/user_data/configs/backtest_entrystudy.json \
  --strategy-list EntryVolConfirm \
  --timerange 20230101-20230301 --export none
'
# Estudios largos (5 años): nohup dentro del CT.
```

## Quirks freqtrade 2026.7
- `--datadir` apunta a la carpeta de klines (`data/coinbase/`), no al userdir raíz.
- Config EXIGE: `pairlists:[{StaticPairList}]`, `entry_pricing`, `exit_pricing`, `order_types`.
- Export trades → zip auto-nombrado en `backtest_results/`; leer con `.last_result.json` + `latest_backtest`.
- `--strategy-list A B C` evalúa varias estrategias en UNA pasada.
