# gemini_analysis.py

import os
import pandas as pd
import glob
import json
import google.generativeai as genai
import config

# --- ADVERTENCIA DE USO ---
# ESTE SCRIPT UTILIZA IA GENERATIVA. LA INFORMACIÓN PUEDE SER IMPRECISA O ESTAR DESACTUALIZADA.
# NO ES UNA RECOMENDACIÓN FINANCIERA. SIEMPRE REALIZA TU PROPIA INVESTIGACIÓN (DYOR).

# --- CONFIGURACIÓN DE LA API DE GEMINI ---
try:
    genai.configure(api_key=config.gemini_api_key)
except AttributeError:
    print("FATAL: No se encontró 'gemini_api_key' en config.py.")
    exit()

if "TU_API_KEY_DE_GEMINI" in config.gemini_api_key:
    print("FATAL: Por favor, configura tu 'gemini_api_key' en el archivo config.py.")
    exit()

def find_latest_csv():
    """Encuentra el archivo .csv de análisis técnico más reciente."""
    list_of_files = glob.glob('analisis_binance_*.csv')
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def build_analysis_prompt(project_name):
    """
    Crea un prompt optimizado y estructurado para la IA.
    Le pide a la IA que devuelva la respuesta en formato JSON para un procesamiento fiable.
    """
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
    """
    Llama a la API de Gemini para obtener el análisis y parsea la respuesta JSON.
    """
    project_name = symbol.replace('USDT', '')
    print(f"   - Enviando {project_name} a Gemini para análisis...")
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = build_analysis_prompt(project_name)
        response = model.generate_content(prompt)
        
        # Limpiar la respuesta para asegurar que sea un JSON válido
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        
        # Parsear el string JSON a un diccionario de Python
        analysis = json.loads(cleaned_response)
        analysis['symbol'] = symbol # Añadir el símbolo al resultado
        return analysis

    except Exception as e:
        print(f"   - ERROR al analizar {project_name}: {e}")
        return {
            "symbol": symbol,
            "risk_level": "Error de Análisis",
            "summary": f"No se pudo completar el análisis debido a un error: {str(e)}",
            "long_term_outlook": "N/A", "medium_term_outlook": "N/A", "short_term_outlook": "N/A"
        }

if __name__ == "__main__":
    csv_file = find_latest_csv()
    if not csv_file:
        print("❌ Error: No se encontró 'analisis_binance_*.csv'. Ejecuta 'main.py' primero.")
        exit()

    print(f"Cargando candidatos técnicos desde: {csv_file}\n")
    df = pd.read_csv(csv_file)
    top_candidates = df.head(20)

    final_results = []
    
    print("--- Iniciando Análisis Fundamental con IA (Gemini) ---")
    for index, row in top_candidates.iterrows():
        symbol = row['simbolo']
        print(f"\nAnalizando Candidato [{index+1}/{len(top_candidates)}]: {symbol} (Puntaje Técnico: {row['score']:.2f})")
        
        # La llamada real a la IA
        ai_analysis = analyze_with_gemini(symbol)
        final_results.append(ai_analysis)

    # --- PRESENTACIÓN DEL INFORME FINAL ---
    print("\n\n" + "="*80)
    print("      INFORME FINAL DE ANÁLISIS FUNDAMENTAL Y TÉCNICO")
    print("="*80)
    
    if not final_results:
        print("No se pudo completar el análisis para ningún candidato.")
    else:
        df_final = pd.DataFrame(final_results)
        
        print("\n--- 💎 Resumen de Proyectos Analizados 💎 ---\n")
        for _, row in df_final.iterrows():
            print(f"📈 SÍMBOLO: {row['symbol']}")
            print(f"   - Riesgo Fundamental: {row['risk_level']}")
            print(f"   - Resumen del Proyecto: {row['summary']}")
            print(f"\n   - 📜 LARGO PLAZO: {row['long_term_outlook']}")
            print(f"   - 📈 MEDIANO PLAZO (Swing): {row['medium_term_outlook']}")
            print(f"   - ⚡ CORTO PLAZO (Day Trading): {row['short_term_outlook']}")
            print("-" * 80)
            
        # Opcional: Guardar el informe final en un nuevo CSV
        try:
            nombre_informe = f"informe_gemini_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
            df_final.to_csv(nombre_informe, index=False)
            print(f"\n✅ Informe detallado guardado en: {nombre_informe}")
        except:
            pass