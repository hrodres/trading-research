# SETUP — freqtrade nativo

Los backtests corren con **freqtrade instalado de forma nativa** en un contenedor
LXC dedicado (Proxmox). Entorno autocontenido: `/opt/freqtrade/user_data/`.

## Infra
- Contenedor LXC dedicado (Proxmox). Debian 13, 4 cores / 4 GB RAM, 8 GB disco.
- Acceso: `pct exec <CT_ID> -- ...` desde el host Proxmox.
- freqtrade 2026.7 en venv `/opt/ft`.

## Instalación reproducible
```bash
pct create <CT_ID> local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst \
  --cores 4 --memory 4096 --swap 1024 --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --hostname freqtrade-native --unprivileged 1
pct start <CT_ID>

pct exec <CT_ID> -- bash -c '
apt-get update -y
apt-get install -y python3-venv python3-pip git curl build-essential pkg-config libta-lib-dev
python3 -m venv /opt/ft
/opt/ft/bin/pip install --upgrade pip wheel
/opt/ft/bin/pip install -r requirements.txt
/opt/ft/bin/freqtrade --version
'
pct exec <CT_ID> -- mkdir -p /opt/freqtrade/user_data/{data/coinbase,strategies,scripts,configs,results}
```

## Klines
Descargar 9 pares Coinbase 2h a `/opt/freqtrade/user_data/data/coinbase/<PAR>_USDT-2h.feather`.

## Correr un backtest
```bash
pct exec <CT_ID> -- bash -c '
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

## Lecciones aprendidas (no repetir errores)
- **`--strategy` recibe el NOMBRE DE LA CLASE**, no el del archivo. `atr_sl_long.py` → clase `AtrSlLong`. Pasar `atr_sl_long` da `Impossible to load Strategy ... class does not exist or contains Python code errors`. El nombre de clase debe ser el CamelCase exacto del archivo (`partialtp_long.py` → `PartialtpLong`, NO `PartialTpLong`).
- **El error "contains Python code errors" es engañoso**: casi siempre es nombre de clase incorrecto, no un error de sintaxis. `py_compile` NO lo detecta (solo compila). Verificar con un smoke test real (1 estrategia + timerange válido + leer el log) o cargando el módulo con `importlib` dentro del CT.
- **Lanzar jobs largos en CT 113**: `pct exec 113 -- nohup ... &` y `setsid ... &` MUEREN al salir el exec (el CT mata el grupo de procesos). CT 113 corre **systemd (PID 1)** → usar `systemd-run --unit=nombre /bin/bash script.sh` (sobrevive al exec; verificar con `systemctl is-active nombre.service`).
- **Transferir archivos al CT**: `cat f | ssh pct exec 'cat > dest'` corrompe el contenido. Usar `base64 f | ssh pct exec 'base64 -d > dest'`.
- **Smoke test antes de lanzar en masa**: 1 estrategia + timerange con datos (BTC/ETH empiezan 2021-05-04, no 2021-01-01; un rango como `20210101-20210201` da `No data found`). Confirmar `EXIT=0` y trades > 0 antes de lanzar las N.
- **No declarar "en marcha" sin verificar desde una conexión nueva**: `systemctl is-active` + `pgrep -c freqtrade` + conteo de zips/JSON. En la espiral de esta sesión, una sola causa raíz (nombre de clase) explicó los 20 fallos iniciales.
