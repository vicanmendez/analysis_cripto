from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from binance.client import Client
import config
from datetime import datetime
import os
import glob
import json
import google.generativeai as genai
import threading
import time

app = Flask(__name__)

# Configuración de APIs
try:
    api_key = config.binance_api_key
    api_secret = config.binance_api_secret
    genai.configure(api_key=config.gemini_api_key)
except AttributeError:
    print("FATAL: No se encontraron las claves en config.py.")
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

# Variables globales para el estado de la aplicación
analysis_status = {
    'is_running': False,
    'progress': 0,
    'total_symbols': 0,
    'current_symbol': '',
    'results': [],
    'error': None,
    'config': {
        'intervalo': Client.KLINE_INTERVAL_1DAY,
        'dias': 350,
        'categoria': 'todos'
    }
}

# --- FUNCIONES DEL MAIN.PY ---
def obtener_simbolos_spot(quote_asset='USDT'):
    """Obtiene una lista de todos los símbolos del mercado SPOT que están actualmente en TRADING."""
    client = Client(api_key, api_secret)
    simbolos_filtrados = []
    try:
        exchange_info = client.get_exchange_info()
        for s in exchange_info['symbols']:
            if s['isSpotTradingAllowed'] and s['status'] == 'TRADING' and s['quoteAsset'] == quote_asset and 'UP' not in s['symbol'] and 'DOWN' not in s['symbol'] and s['baseAsset'] not in ['USDC', 'TUSD', 'BUSD']:
                simbolos_filtrados.append(s['symbol'])
        return simbolos_filtrados
    except Exception as e:
        print(f"Error al obtener símbolos: {e}")
        return []

def obtener_info_simbolos_detallada(quote_asset='USDT'):
    """Obtiene información detallada de todos los símbolos incluyendo volumen y otros datos."""
    client = Client(api_key, api_secret)
    simbolos_info = []
    
    try:
        # Obtener información del exchange
        exchange_info = client.get_exchange_info()
        
        # Obtener estadísticas de 24h para todos los símbolos
        ticker_24h = client.get_ticker()
        ticker_dict = {t['symbol']: t for t in ticker_24h}
        
        for s in exchange_info['symbols']:
            if (s['isSpotTradingAllowed'] and s['status'] == 'TRADING' and 
                s['quoteAsset'] == quote_asset and 'UP' not in s['symbol'] and 
                'DOWN' not in s['symbol'] and s['baseAsset'] not in ['USDC', 'TUSD', 'BUSD']):
                
                symbol_info = {
                    'symbol': s['symbol'],
                    'baseAsset': s['baseAsset'],
                    'quoteAsset': s['quoteAsset'],
                    'onboardDate': s.get('onboardDate', None),  # Fecha de listado
                    'permissions': s.get('permissions', []),
                    'volume_24h': 0,
                    'quoteVolume_24h': 0,
                    'count_24h': 0,
                    'priceChange_24h': 0,
                    'priceChangePercent_24h': 0
                }
                
                # Añadir datos de volumen si están disponibles
                if s['symbol'] in ticker_dict:
                    ticker = ticker_dict[s['symbol']]
                    symbol_info.update({
                        'volume_24h': float(ticker.get('volume', 0)),
                        'quoteVolume_24h': float(ticker.get('quoteVolume', 0)),
                        'count_24h': int(ticker.get('count', 0)),
                        'priceChange_24h': float(ticker.get('priceChange', 0)),
                        'priceChangePercent_24h': float(ticker.get('priceChangePercent', 0))
                    })
                
                simbolos_info.append(symbol_info)
        
        return simbolos_info
        
    except Exception as e:
        print(f"Error al obtener información detallada de símbolos: {e}")
        return []

def filtrar_simbolos_por_categoria(simbolos_info, categoria='todos'):
    """
    Filtra símbolos por diferentes categorías.
    
    Categorías disponibles:
    - 'todos': Todos los símbolos
    - 'populares': Top 50 por volumen de trading
    - 'nuevos': Listados en los últimos 30 días
    - 'top10': Top 10 por volumen
    - 'top100': Top 100 por volumen
    - 'bajos_volumen': Símbolos con bajo volumen (para encontrar gemas ocultas)
    - 'alto_volatilidad': Símbolos con alta volatilidad (cambio de precio > 10%)
    """
    
    if not simbolos_info:
        return []
    
    if categoria == 'todos':
        return [s['symbol'] for s in simbolos_info]
    
    # Ordenar por volumen de trading (descendente)
    simbolos_ordenados = sorted(simbolos_info, key=lambda x: x['quoteVolume_24h'], reverse=True)
    
    if categoria == 'populares':
        # Top 50 por volumen
        return [s['symbol'] for s in simbolos_ordenados[:50]]
    
    elif categoria == 'top10':
        # Top 10 por volumen
        return [s['symbol'] for s in simbolos_ordenados[:10]]
    
    elif categoria == 'top100':
        # Top 100 por volumen
        return [s['symbol'] for s in simbolos_ordenados[:100]]
    
    elif categoria == 'nuevos':
        # Listados en los últimos 30 días
        from datetime import datetime, timedelta
        fecha_limite = datetime.now() - timedelta(days=30)
        nuevos = []
        
        for s in simbolos_info:
            if s['onboardDate']:
                try:
                    fecha_listado = datetime.fromtimestamp(s['onboardDate'] / 1000)
                    if fecha_listado >= fecha_limite:
                        nuevos.append(s['symbol'])
                except:
                    continue
        
        return nuevos
    
    elif categoria == 'bajos_volumen':
        # Símbolos con bajo volumen (últimos 100 por volumen)
        return [s['symbol'] for s in simbolos_ordenados[-100:]]
    
    elif categoria == 'alto_volatilidad':
        # Símbolos con alta volatilidad (>10% cambio en 24h)
        volatiles = []
        for s in simbolos_info:
            if abs(s['priceChangePercent_24h']) > 10:
                volatiles.append(s['symbol'])
        return volatiles
    
    else:
        # Categoría no reconocida, devolver todos
        return [s['symbol'] for s in simbolos_info]

def obtener_categorias_disponibles():
    """Retorna las categorías disponibles para filtrar símbolos."""
    return {
        'todos': 'Todos los Símbolos',
        'populares': 'Top 50 Populares',
        'top10': 'Top 10 por Volumen',
        'top100': 'Top 100 por Volumen',
        'nuevos': 'Nuevos Listados (30 días)',
        'bajos_volumen': 'Bajo Volumen (Gemas Ocultas)',
        'alto_volatilidad': 'Alta Volatilidad (>10%)'
    }

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

def calcular_sma(data, length):
    return data.rolling(window=length).mean()

def calcular_rsi(data, length=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    if avg_loss.iloc[-1] == 0: return 100.0
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
    """Verifica si los datos cumplen con la ESTRATEGIA FLEXIBLE de tendencia alcista."""
    if df is None or len(df) < 1:
        return False, None

    ultima_vela = df.iloc[-1]

    # Condiciones flexibilizadas
    cond_tendencia_alcista = ultima_vela['SMA_50'] > ultima_vela['SMA_200']
    cond_rsi = 45 < ultima_vela['RSI_14'] < 80
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

# --- FUNCIONES DEL GEMINI-ANALYSIS.PY ---
def build_analysis_prompt(project_name):
    """Crea un prompt optimizado para la IA."""
    return f"""
    Actúa como un analista financiero experto en criptomonedas, escéptico y centrado en los fundamentales.
    Analiza el proyecto de criptomoneda: "{project_name}".

    Basándote en información pública y verificable (casos de uso reales, equipo, tokenomics, actividad de desarrollo en repositorios como GitHub, comunidad, auditorías de seguridad, y posibles "red flags" o riesgos), proporciona un análisis conciso.

    Devuelve tu respuesta ÚNICAMENTE como un objeto JSON con la siguiente estructura y claves:
    {{
      "risk_level": "string",
      "summary": "string",
      "long_term_outlook": "string",
      "medium_term_outlook": "string",
      "short_term_outlook": "string"
    }}

    Instrucciones para cada clave:
    - "risk_level": Clasifica el riesgo fundamental como "Bajo", "Medio", "Alto" o "Muy Alto / Estafa Potencial".
    - "summary": Un resumen de 1 a 2 frases sobre qué es el proyecto y cuál es su principal fortaleza o debilidad.
    - "long_term_outlook": Análisis para inversión a largo plazo (1-3 años). Evalúa si tiene potencial de adopción masiva o si es probable que quede obsoleto. Sé crítico.
    - "medium_term_outlook": Análisis para Swing Trading (semanas a meses). Evalúa si se ve afectado por narrativas, eventos del roadmap o si su volatilidad es predecible.
    - "short_term_outlook": Análisis para Day Trading. Evalúa si tiene la liquidez y volatilidad necesarias. Menciona si es sensible a noticias diarias.

    No incluyas disclaimers, introducciones ni texto adicional. Solo el objeto JSON.
    """

def analyze_with_gemini(symbol):
    """Llama a la API de Gemini para obtener el análisis."""
    project_name = symbol.replace('USDT', '')
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = build_analysis_prompt(project_name)
        response = model.generate_content(prompt)
        
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        analysis = json.loads(cleaned_response)
        analysis['symbol'] = symbol
        return analysis

    except Exception as e:
        return {
            "symbol": symbol,
            "risk_level": "Error de Análisis",
            "summary": f"No se pudo completar el análisis debido a un error: {str(e)}",
            "long_term_outlook": "N/A", 
            "medium_term_outlook": "N/A", 
            "short_term_outlook": "N/A"
        }

def find_latest_csv():
    """Encuentra el archivo .csv de análisis técnico más reciente."""
    list_of_files = glob.glob('analisis_binance_*.csv')
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def validar_configuracion(intervalo, dias):
    """Valida que la configuración sea apropiada para el análisis."""
    # Para intervalos muy pequeños, limitar la cantidad de días para evitar demasiados datos
    if intervalo in [Client.KLINE_INTERVAL_1SECOND, Client.KLINE_INTERVAL_1MINUTE]:
        if dias > 7:
            return False, "Para intervalos de 1 segundo o 1 minuto, se recomienda máximo 7 días."
    
    # Para intervalos pequeños, limitar días para evitar sobrecarga
    elif intervalo in [Client.KLINE_INTERVAL_3MINUTE, Client.KLINE_INTERVAL_5MINUTE]:
        if dias > 30:
            return False, "Para intervalos pequeños, se recomienda máximo 30 días."
    
    return True, None

# --- FUNCIÓN DE ANÁLISIS EN BACKGROUND ---
def run_technical_analysis():
    """Ejecuta el análisis técnico en background."""
    global analysis_status
    
    try:
        analysis_status['is_running'] = True
        analysis_status['progress'] = 0
        analysis_status['error'] = None
        analysis_status['results'] = []
        
        # Obtener configuración actual
        intervalo = analysis_status['config']['intervalo']
        dias = analysis_status['config']['dias']
        categoria = analysis_status['config'].get('categoria', 'todos')
        
        # Validar configuración
        es_valido, mensaje_error = validar_configuracion(intervalo, dias)
        if not es_valido:
            analysis_status['error'] = mensaje_error
            analysis_status['is_running'] = False
            return
        
        # Obtener información detallada de símbolos
        print(f"Obteniendo información detallada de símbolos...")
        simbolos_info = obtener_info_simbolos_detallada(quote_asset='USDT')
        if not simbolos_info:
            analysis_status['error'] = "No se pudo obtener la información de símbolos."
            analysis_status['is_running'] = False
            return
        
        # Filtrar símbolos por categoría
        symbols_a_analizar = filtrar_simbolos_por_categoria(simbolos_info, categoria)
        if not symbols_a_analizar:
            analysis_status['error'] = f"No se encontraron símbolos para la categoría '{categoria}'."
            analysis_status['is_running'] = False
            return
        
        analysis_status['total_symbols'] = len(symbols_a_analizar)
        resultados_positivos = []

        for i, symbol in enumerate(symbols_a_analizar):
            if not analysis_status['is_running']:  # Check if cancelled
                break
                
            analysis_status['current_symbol'] = symbol
            analysis_status['progress'] = int((i / len(symbols_a_analizar)) * 100)
            
            df_historico = obtener_datos_historicos_binance(symbol, intervalo, dias)
            if df_historico.empty: 
                continue

            df_con_indicadores = calcular_indicadores(df_historico.copy())
            hay_senal, detalles = verificar_senal_de_compra(df_con_indicadores)
            
            if hay_senal:
                detalles['simbolo'] = symbol
                resultados_positivos.append(detalles)

        # Guardar resultados
        if resultados_positivos:
            resultados_ordenados = sorted(resultados_positivos, key=lambda x: x['score'], reverse=True)
            df_resultados = pd.DataFrame(resultados_ordenados)
            df_resultados = df_resultados[['simbolo', 'score', 'precio_cierre', 'rsi', 'vol_ratio']]
            
            nombre_archivo = f"analisis_binance_{categoria}_{intervalo}_{dias}dias_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            df_resultados.to_csv(nombre_archivo, index=False, float_format='%.2f')
            
            analysis_status['results'] = df_resultados.to_dict('records')
        
        analysis_status['progress'] = 100
        analysis_status['is_running'] = False
        
    except Exception as e:
        analysis_status['error'] = str(e)
        analysis_status['is_running'] = False

# --- RUTAS DE FLASK ---
@app.route('/')
def index():
    return render_template('index.html', 
                         intervalos=INTERVALOS_DISPONIBLES,
                         categorias=obtener_categorias_disponibles())

@app.route('/api/start-analysis', methods=['POST'])
def start_analysis():
    """Inicia el análisis técnico en background."""
    global analysis_status
    
    if analysis_status['is_running']:
        return jsonify({'error': 'Análisis ya en progreso'}), 400
    
    # Obtener configuración del usuario
    data = request.get_json()
    intervalo_input = data.get('intervalo', '1d')
    dias = data.get('dias', 350)
    categoria = data.get('categoria', 'todos')
    
    # Validar intervalo
    if intervalo_input not in INTERVALOS_DISPONIBLES:
        return jsonify({'error': 'Intervalo no válido'}), 400
    
    intervalo = INTERVALOS_DISPONIBLES[intervalo_input]
    
    # Validar días
    if not isinstance(dias, int) or dias < 30 or dias > 1000:
        return jsonify({'error': 'La cantidad de días debe estar entre 30 y 1000'}), 400
    
    # Validar categoría
    categorias_disponibles = obtener_categorias_disponibles()
    if categoria not in categorias_disponibles:
        return jsonify({'error': 'Categoría no válida'}), 400
    
    # Validar configuración
    es_valido, mensaje_error = validar_configuracion(intervalo, dias)
    if not es_valido:
        return jsonify({'error': mensaje_error}), 400
    
    # Actualizar configuración
    analysis_status['config']['intervalo'] = intervalo
    analysis_status['config']['dias'] = dias
    analysis_status['config']['categoria'] = categoria
    
    # Reset status
    analysis_status['is_running'] = False
    analysis_status['progress'] = 0
    analysis_status['total_symbols'] = 0
    analysis_status['current_symbol'] = ''
    analysis_status['results'] = []
    analysis_status['error'] = None
    
    # Start analysis in background thread
    thread = threading.Thread(target=run_technical_analysis)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Análisis iniciado',
        'config': {
            'intervalo': intervalo_input,
            'dias': dias,
            'categoria': categoria
        }
    })

@app.route('/api/analysis-status')
def get_analysis_status():
    """Obtiene el estado actual del análisis."""
    return jsonify(analysis_status)

@app.route('/api/add-symbol', methods=['POST'])
def add_symbol():
    """Añade un símbolo manualmente al análisis."""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    intervalo_input = data.get('intervalo', '1d')
    dias = data.get('dias', 350)
    
    if not symbol:
        return jsonify({'error': 'Símbolo requerido'}), 400
    
    # Validar intervalo
    if intervalo_input not in INTERVALOS_DISPONIBLES:
        return jsonify({'error': 'Intervalo no válido'}), 400
    
    intervalo = INTERVALOS_DISPONIBLES[intervalo_input]
    
    # Validar días
    if not isinstance(dias, int) or dias < 30 or dias > 1000:
        return jsonify({'error': 'La cantidad de días debe estar entre 30 y 1000'}), 400
    
    # Añadir USDT si no está presente
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    # Analizar el símbolo
    df_historico = obtener_datos_historicos_binance(symbol, intervalo, dias)
    if df_historico.empty:
        return jsonify({'error': f'No se pudieron obtener datos para {symbol}'}), 400
    
    df_con_indicadores = calcular_indicadores(df_historico.copy())
    hay_senal, detalles = verificar_senal_de_compra(df_con_indicadores)
    
    if hay_senal:
        detalles['simbolo'] = symbol
        return jsonify({
            'success': True,
            'result': detalles,
            'message': f'{symbol} cumple con los criterios técnicos'
        })
    else:
        return jsonify({
            'success': False,
            'message': f'{symbol} no cumple con los criterios técnicos'
        })

@app.route('/api/analyze-with-ai', methods=['POST'])
def analyze_with_ai():
    """Analiza símbolos con IA de Gemini."""
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols:
        return jsonify({'error': 'Lista de símbolos requerida'}), 400
    
    results = []
    for symbol in symbols:
        analysis = analyze_with_gemini(symbol)
        results.append(analysis)
    
    return jsonify({'results': results})

@app.route('/api/download-csv')
def download_csv():
    """Descarga el archivo CSV más reciente."""
    csv_file = find_latest_csv()
    if not csv_file:
        return jsonify({'error': 'No se encontró archivo CSV'}), 404
    
    return send_file(csv_file, as_attachment=True)

@app.route('/api/get-latest-results')
def get_latest_results():
    """Obtiene los resultados del CSV más reciente."""
    csv_file = find_latest_csv()
    if not csv_file:
        return jsonify({'error': 'No se encontró archivo CSV'}), 404
    
    try:
        df = pd.read_csv(csv_file)
        return jsonify({'results': df.to_dict('records')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-categories')
def get_categories():
    """Obtiene las categorías disponibles para filtrar símbolos."""
    return jsonify({
        'categories': obtener_categorias_disponibles()
    })

@app.route('/api/get-symbols-info')
def get_symbols_info():
    """Obtiene información detallada de todos los símbolos."""
    try:
        simbolos_info = obtener_info_simbolos_detallada(quote_asset='USDT')
        return jsonify({
            'symbols': simbolos_info,
            'total': len(simbolos_info)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 