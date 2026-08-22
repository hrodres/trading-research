# SETUP — freqtrade nativo (sin Docker)

Este proyecto corre los backtests con **freqtrade instalado de forma nativa** en un
CT dedicado de Proxmox (**CT 113, `freqtrade-native`, Debian 13**). Se migró desde
el contenedor Docker `freqtrade` de CT 112 para eliminar la capa Docker (el `ENTRYPOINT
[freqtrade]` de la imagen obligaba a usar `docker run --entrypoint python` para correr
scripts como proceso principal, y el container moría al salir el `freqtrade trade`).

## Por qué nativo y no Docker
- freqtrade no es un daemon: el container Docker `freqtrade` corre `freqtrade trade` y
  sale (code 2). Lanzar backtests con `docker exec -d` moría cuando el container principal salía.
- Imagen `freqtradeorg/freqtrade:stable` tiene `ENTRYPOINT [freqtrade]` → para correr un
  script Python como proceso principal había que usar `docker run -d --entrypoint python ...`.
- Con CT nativo: `python3 script.py` funciona directo y sobrevive con `nohup` (el CT es LXC persistente).

## CT 113 (infra homelab)
- Proxmox `pve` (192.168.1.222). VMID **113**, hostname `freqtrade-native`, Debian 13.
- Recursos: 4 cores, 4 GB RAM, 1 GB swap, **disco 8 GB en storage `local-lvm`**.
  > Nota: en este nodo el único storage con content `rootdir` (CT) es `local-lvm`
  > (94% usado). 8 GB cabe pero deja el thin pool casi lleno. Si crece, usar ≥12 GB.
- IP: **192.168.1.58** (DHCP). Acceso: `pct exec 113 -- ...` desde el host.
- Todo **autocontenido** dentro del CT (sin bind mount al host): `/opt/freqtrade/user_data/`.

## Instalación (reproducible)
```bash
# 1) Crear CT (desde plantilla debian-13 ya descargada en el nodo)
pct create 113 local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst \
  --cores 4 --memory 4096 --swap 1024 --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --hostname freqtrade-native --unprivileged 1 --onboot 0
pct start 113

# 2) Dentro del CT: venv + freqtrade nativo
pct exec 113 -- bash -c '
apt-get update -y
apt-get install -y python3-venv python3-pip git curl build-essential pkg-config libta-lib-dev
python3 -m venv /opt/ft
/opt/ft/bin/pip install --upgrade pip wheel
/opt/ft/bin/pip install -r requirements.txt   # trae freqtrade==2026.7 + pyarrow
/opt/ft/bin/freqtrade --version                # freqtrade 2026.7, ccxt 4.5.75, Python 3.13.5
'

# 3) Estructura autocontenida
pct exec 113 -- mkdir -p /opt/freqtrade/user_data/{data/coinbase,strategies,scripts,configs,results}

# 4) Migrar klines 9 pares desde CT 112 (donde estaban en /docker/freqtrade/user_data/data/coinbase)
#    pct pull 112 <origen> /tmp/k.feather ; pct push 113 /tmp/k.feather <destino>
#    destino: /opt/freqtrade/user_data/data/coinbase/<PAR>_USDT-2h.feather
```

## Cómo correr un backtest / estudio en 113
```bash
pct exec 113 -- bash -c '
cd /opt/freqtrade
/opt/ft/bin/freqtrade backtesting \
  --userdir /opt/freqtrade/user_data --datadir /opt/freqtrade/user_data/data/coinbase \
  --config /opt/freqtrade/user_data/configs/backtest_exitstudy.json \
  --strategy-list ExitFixedWide ExitTrailing ExitEmaCross ExitTimeStop \
  --timerange 20230101-20230301 --export none
'
# Para estudios largos (5 anos), usar container efimero o nohup dentro del CT:
#   pct exec 113 -- bash -c "nohup /opt/ft/bin/python /opt/freqtrade/user_data/scripts/exit_study.py > results/exitstudy_C.log 2>&1 &"
```

## Legacy: Docker en CT 112 (DESHABILITADO)
- El container Docker `freqtrade` en CT 112 quedó con `RestartPolicy: no` (no arranca solo en reboot).
- Los datos/klines ya NO se usan desde ahí; fuente activa = CT 113.
- Para referencia histórica: `docker run -d --entrypoint python -v /docker/freqtrade/user_data:/freqtrade/user_data freqtradeorg/freqtrade:stable script.py`.

## Quirks freqtrade 2026.7 (válidos en nativo y Docker)
- `--datadir` debe apuntar a la carpeta de klines (`data/coinbase/`), no al userdir raíz.
- Config EXIGE: `pairlists:[{StaticPairList}]`, `entry_pricing`, `exit_pricing`, `order_types`.
- Export trades → zip auto-nombrado en `backtest_results/`; leer con `.last_result.json`
  + `latest_backtest`, luego `d["strategy"][NOMBRE]["trades"]`.
- `--strategy-list A B C D` evalúa varias estrategias en UNA pasada (más eficiente).
- `custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs)`
  devuelve `str | bool | None`.
