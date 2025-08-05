#!/usr/bin/env python3
"""
Script para ejecutar la webapp CryptoScanner Pro
"""

from app import app

if __name__ == '__main__':
    print("🚀 Iniciando CryptoScanner Pro WebApp...")
    print("📱 Interfaz web disponible en: http://localhost:5000")
    print("⚠️  Asegúrate de tener configuradas las APIs en config.py")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000) 