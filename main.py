# main.py

import pandas as pd
import numpy as np
from binance.client import Client
import config 
from datetime import datetime

# --- ADVERTENCIA DE USO ---
# Este script es para fines educativos y no constituye una recomendación financiera.

# --- CARGA DE CLAVES DE API ---
try:
    api_key = config.binance_api_key
    api_secret = config.binance_api_secret
except AttributeError:
    print("FATAL: No se encontraron las claves en tu archivo config.py.")
    exit()

if "TU_API_KEY" in api_key or "TU_SECRET_KEY" in api_secret:
    print("FATAL: Por favor, configura tus claves de API en config.py antes de ejecutar.")
    exit()

# --- CONFIGURACIÓN DE INTERVALOS DISPONIBLES ---
INTERVALOS_DISPONIBLES = {
    '1s': Client.KLINE_INTERVAL_1SECOND,
    '1m': Client.KLINE_INTERVAL_1MINUTE,
    '3m': Client.KLINE_INTERVAL_3MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '6h': Client.KLINE_INTERVAL_6HOUR,
    '8h': Client.KLINE_INTERVAL_8HOUR,
    '12h': Client.KLINE_INTERVAL_12HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '3d': Client.KLINE_INTERVAL_3DAY,
    '1w': Client.KLINE_INTERVAL_1WEEK,
    '1M': Client.KLINE_INTERVAL_1MONTH
}

def obtener_configuracion_usuario():
    """
    Permite al usuario configurar el intervalo de tiempo y la cantidad de días para el análisis.
    """
    print("\n=== CONFIGURACIÓN DE ANÁLISIS ===")
    print("Intervalos disponibles:")
    for key, value in INTERVALOS_DISPONIBLES.items():
        print(f"  {key}: {value}")
    
    # Configurar intervalo
    while True:
        intervalo_input = input("\nIngrese el intervalo deseado (ej: 1m, 5m, 1h, 1d): ").strip()
        if intervalo_input in INTERVALOS_DISPONIBLES:
            intervalo = INTERVALOS_DISPONIBLES[intervalo_input]
            break
        else:
            print("❌ Intervalo no válido. Por favor, seleccione uno de la lista.")
    
    # Configurar días
    while True:
        try:
            dias = int(input("Ingrese la cantidad de días para el análisis (mínimo 30, máximo 1000): "))
            if 30 <= dias <= 1000:
                break
            else:
                print("❌ La cantidad de días debe estar entre 30 y 1000.")
        except ValueError:
            print("❌ Por favor, ingrese un número válido.")
    
    return intervalo, dias

def validar_configuracion(intervalo, dias):
    """
    Valida que la configuración sea apropiada para el análisis.
    """
    # Para intervalos muy pequeños, limitar la cantidad de días para evitar demasiados datos
    if intervalo in [Client.KLINE_INTERVAL_1SECOND, Client.KLINE_INTERVAL_1MINUTE]:
        if dias > 7:
            print("⚠️  ADVERTENCIA: Para intervalos de 1 segundo o 1 minuto, se recomienda máximo 7 días.")
            confirmacion = input("¿Desea continuar con esta configuración? (s/n): ").lower()
            if confirmacion != 's':
                return False
    
    # Para intervalos pequeños, limitar días para evitar sobrecarga
    elif intervalo in [Client.KLINE_INTERVAL_3MINUTE, Client.KLINE_INTERVAL_5MINUTE]:
        if dias > 30:
            print("⚠️  ADVERTENCIA: Para intervalos pequeños, se recomienda máximo 30 días.")
            confirmacion = input("¿Desea continuar con esta configuración? (s/n): ").lower()
            if confirmacion != 's':
                return False
    
    return True

# --- FUNCIONES DE OBTENCIÓN DE DATOS ---
def obtener_simbolos_spot(quote_asset='USDT'):
    """Obtiene una lista de todos los símbolos del mercado SPOT que están actualmente en TRADING."""
    print(f"Obteniendo todos los símbolos que operan contra {quote_asset}...")
    client = Client(api_key, api_secret)
    simbolos_filtrados = []
    try:
        exchange_info = client.get_exchange_info()
        for s in exchange_info['symbols']:
            # Añadimos un filtro para excluir los pares de stablecoins como 'USDCUSDT'
            if s['isSpotTradingAllowed'] and s['status'] == 'TRADING' and s['quoteAsset'] == quote_asset and 'UP' not in s['symbol'] and 'DOWN' not in s['symbol'] and s['baseAsset'] not in ['USDC', 'TUSD', 'BUSD']:
                simbolos_filtrados.append(s['symbol'])
        print(f"Se encontraron {len(simbolos_filtrados)} símbolos para analizar.")
        return simbolos_filtrados
    except Exception as e:
        print(f"Ocurrió un error al obtener la lista de símbolos: {e}")
        return []

def obtener_datos_historicos_binance(simbolo, intervalo, dias):
    """Obtiene los datos históricos desde la API de Binance."""
    client = Client(api_key, api_secret)
    fecha_inicio = f"{dias} days ago UTC"
    try:
        klines = client.get_historical_klines(simbolo, intervalo, fecha_inicio)
    except Exception as e:
        print(f"Error obteniendo datos para {simbolo}: {e}")
        return pd.DataFrame()

    columnas = ['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore']
    df = pd.DataFrame(klines, columns=columnas)
    if df.empty: return df
    
    cols_num = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in cols_num:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    return df

# --- CALCULADORAS DE INDICADORES ---
def calcular_sma(data, length):
    return data.rolling(window=length).mean()

def calcular_rsi(data, length=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    if avg_loss.iloc[-1] == 0: return 100.0 # Evitar división por cero si no hay pérdidas
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_indicadores(df):
    """Añade las columnas de indicadores al DataFrame."""
    if df is None or df.empty: return pd.DataFrame()
    df['SMA_50'] = calcular_sma(df['Close'], 50)
    df['SMA_200'] = calcular_sma(df['Close'], 200)
    df['RSI_14'] = calcular_rsi(df['Close'], 14)
    df['VOLUME_SMA_20'] = calcular_sma(df['Volume'], 20)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def verificar_senal_de_compra(df):
    """
    Verifica si los datos cumplen con la ESTRATEGIA FLEXIBLE de tendencia alcista.
    """
    if df is None or len(df) < 1:
        return False, None

    ultima_vela = df.iloc[-1]

    # --- CONDICIONES FLEXIBILIZADAS ---
    # 1. TENDENCIA: El precio está en un "estado dorado" (SMA50 por encima de SMA200).
    cond_tendencia_alcista = ultima_vela['SMA_50'] > ultima_vela['SMA_200']
    
    # 2. MOMENTUM: El RSI está en un rango saludable (ni sobrevendido ni excesivamente sobrecomprado).
    cond_rsi = 45 < ultima_vela['RSI_14'] < 80
    
    # 3. VOLUMEN: El volumen actual confirma el interés del mercado.
    cond_volumen = ultima_vela['Volume'] > ultima_vela['VOLUME_SMA_20'] and ultima_vela['VOLUME_SMA_20'] > 0

    if cond_tendencia_alcista and cond_rsi and cond_volumen:
        vol_ratio = ultima_vela['Volume'] / ultima_vela['VOLUME_SMA_20']
        score = ultima_vela['RSI_14'] * vol_ratio
        
        detalles = {
            "precio_cierre": ultima_vela['Close'],
            "rsi": ultima_vela['RSI_14'],
            "vol_ratio": vol_ratio,
            "score": score
        }
        return True, detalles
    
    return False, None

# --- BLOQUE PRINCIPAL DE EJECUCIÓN ---
if __name__ == "__main__":
    
    # Obtener configuración del usuario
    intervalo, dias = obtener_configuracion_usuario()
    
    # Validar configuración
    if not validar_configuracion(intervalo, dias):
        print("Configuración cancelada por el usuario.")
        exit()
    
    print(f"\n✅ Configuración confirmada:")
    print(f"   - Intervalo: {intervalo}")
    print(f"   - Días de análisis: {dias}")
    
    symbols_a_analizar = obtener_simbolos_spot(quote_asset='USDT')
    if not symbols_a_analizar:
        print("No se pudo obtener la lista de símbolos. Terminando el script.")
        exit()
    
    print(f"\nIniciando análisis con ESTRATEGIA FLEXIBLE. Esto puede tardar varios minutos...")
    
    resultados_positivos = []
    total_symbols = len(symbols_a_analizar)

    for i, symbol in enumerate(symbols_a_analizar):
        print(f"Progreso: [{i+1}/{total_symbols}] Analizando: {symbol}", end='\r')
        
        df_historico = obtener_datos_historicos_binance(symbol, intervalo, dias)
        if df_historico.empty: continue

        df_con_indicadores = calcular_indicadores(df_historico.copy())
        
        hay_senal, detalles = verificar_senal_de_compra(df_con_indicadores)
        
        if hay_senal:
            detalles['simbolo'] = symbol
            resultados_positivos.append(detalles)
            print(f"\n(+) Candidato encontrado: {symbol}. Recolectando para el informe final.")

    print("\n\nAnálisis completado. Generando informe final...")
    
    if not resultados_positivos:
        print("\n--- INFORME FINAL ---")
        print("No se encontraron instrumentos que cumplan con los criterios de la estrategia flexible hoy.")
        print("El mercado puede estar en una fase de baja volatilidad o tendencia bajista. Inténtalo más tarde.")
    else:
        resultados_ordenados = sorted(resultados_positivos, key=lambda x: x['score'], reverse=True)
        df_resultados = pd.DataFrame(resultados_ordenados)
        df_resultados = df_resultados[['simbolo', 'score', 'precio_cierre', 'rsi', 'vol_ratio']]

        print("\n--- MEJORES INSTRUMENTOS ENCONTRADOS (Estrategia Flexible) ---")
        print(f"Configuración: {intervalo} - {dias} días")
        print(df_resultados.to_string(index=False))
        
        try:
            nombre_archivo = f"analisis_binance_{intervalo}_{dias}dias_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            df_resultados.to_csv(nombre_archivo, index=False, float_format='%.2f')
            print(f"\n✅ Resultados exportados exitosamente a: {nombre_archivo}")
        except Exception as e:
            print(f"\n❌ Ocurrió un error al exportar a CSV: {e}")