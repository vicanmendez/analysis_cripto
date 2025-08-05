# CryptoScanner Pro - WebApp de Análisis de Criptomonedas

Este proyecto consta de una **webapp moderna** que combina análisis técnico automatizado con inteligencia artificial para encontrar y analizar oportunidades de inversión en el mercado de criptomonedas de Binance.

## 🚀 **NUEVA INTERFAZ WEB**

La aplicación ahora incluye una interfaz web elegante y moderna con las siguientes funcionalidades:

### **Funciones Principales:**

1. **🔍 Escáner Técnico Automático**
   - Analiza cientos de símbolos en busca de señales de compra específicas
   - Estrategia: Cruce Dorado + RSI + Volumen
   - Genera archivo CSV con los mejores candidatos
   - Barra de progreso en tiempo real

2. **➕ Añadir Símbolos Manualmente**
   - Permite analizar cualquier criptomoneda específica
   - Verificación instantánea de criterios técnicos
   - Integración con la lista de resultados

3. **🧠 Análisis Fundamental con IA (Gemini)**
   - Análisis de riesgo y fundamentales de cada proyecto
   - Clasificación automática: Largo Plazo, Swing Trading, Day Trading
   - Descarte de proyectos de alto riesgo
   - Análisis de símbolos seleccionados o top candidatos

**DISCLAIMER:** Este software es para fines puramente educativos. No es una recomendación de inversión. Los análisis generados por la IA pueden contener errores u omisiones. Realiza siempre tu propia investigación.

## 📁 Estructura del Proyecto

```
/tu-proyecto/
├── app.py                    # 🆕 Aplicación Flask principal
├── run_webapp.py            # 🆕 Script para ejecutar la webapp
├── main.py                  # Script original de análisis técnico
├── gemini_analysis.py       # Script original de análisis con IA
├── config.py                # Configuración de APIs
├── requirements.txt         # Dependencias actualizadas
├── templates/               # 🆕 Carpeta de templates HTML
│   └── index.html          # 🆕 Interfaz web principal
└── README.md               # Este archivo
```

## 🛠️ Instalación y Configuración

### Paso 1: Configurar APIs
Edita `config.py` con tus claves de API:

```python
binance_api_key="TU_API_KEY_DE_BINANCE"
binance_api_secret="TU_API_SECRET_DE_BINANCE"
gemini_api_key="TU_API_KEY_DE_GEMINI"
```

### Paso 2: Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Paso 3: Ejecutar la WebApp
```bash
python run_webapp.py
```

La aplicación estará disponible en: **http://localhost:5000**

## 🎯 Cómo Usar la WebApp

### **1. Escáner Técnico**
- Haz clic en "Iniciar Análisis" en la tarjeta del Escáner Técnico
- Observa el progreso en tiempo real
- Los resultados se mostrarán automáticamente en una tabla
- Descarga el CSV con "Descargar CSV"

### **2. Añadir Símbolo Manual**
- Escribe el símbolo en el campo de texto (ej: BTC, ETH, ADA)
- Haz clic en el botón "+" o presiona Enter
- El sistema verificará si cumple los criterios técnicos

### **3. Análisis con IA**
- **Opción A**: Haz clic en "Analizar con IA" para analizar los top 10 candidatos
- **Opción B**: Selecciona símbolos específicos de la tabla y haz clic en "Analizar Seleccionados"
- Los resultados se mostrarán con clasificación de riesgo y recomendaciones

## 🔧 Funcionalidades Técnicas

### **Estrategia de Análisis Técnico:**
- **Cruce Dorado**: SMA 50 > SMA 200
- **RSI Saludable**: Entre 45-80 (ni sobrevendido ni sobrecomprado)
- **Confirmación de Volumen**: Volumen actual > Promedio 20 períodos
- **Puntaje**: RSI × Ratio de Volumen

### **Análisis Fundamental con IA:**
- **Nivel de Riesgo**: Bajo, Medio, Alto, Muy Alto/Estafa
- **Análisis por Plazos**: Largo plazo (1-3 años), Swing Trading, Day Trading
- **Factores Evaluados**: Casos de uso, equipo, tokenomics, desarrollo, comunidad

## 📊 Características de la Interfaz

- **🎨 Diseño Moderno**: Interfaz elegante con gradientes y efectos visuales
- **📱 Responsive**: Funciona en desktop, tablet y móvil
- **⚡ Tiempo Real**: Barra de progreso y actualizaciones en vivo
- **🎯 Interactivo**: Selección múltiple, filtros y controles intuitivos
- **📈 Visualización**: Tablas organizadas y badges de estado

## 🔄 Flujo de Trabajo Recomendado

1. **Ejecuta el Escáner Técnico** para obtener candidatos iniciales
2. **Revisa los resultados** en la tabla generada
3. **Añade símbolos específicos** si tienes algún token en mente
4. **Analiza con IA** los candidatos más prometedores
5. **Descarga el CSV** para análisis posterior
6. **Realiza tu propia investigación** (DYOR) antes de invertir

## 🚨 Notas Importantes

- **APIs Requeridas**: Necesitas claves de Binance (solo lectura) y Gemini
- **Tiempo de Análisis**: El escáner puede tardar varios minutos dependiendo del mercado
- **Límites de API**: Respeta los límites de rate de las APIs
- **Resultados**: Los análisis de IA son informativos, no recomendaciones de inversión

## 🐛 Solución de Problemas

### Error de APIs:
- Verifica que las claves en `config.py` sean correctas
- Asegúrate de que las APIs tengan permisos adecuados

### Error de Dependencias:
```bash
pip install --upgrade -r requirements.txt
```

### Puerto Ocupado:
Cambia el puerto en `run_webapp.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Cambia 5000 por otro puerto
```

---

**¡Disfruta usando CryptoScanner Pro! 🚀📈**