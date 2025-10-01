#!/bin/bash
# scripts/health_check.sh

echo "🔍 Verificando estado de los servicios..."

# Verificar faiss_search
echo "Probando faiss_search (puerto 8002)..."
curl -f http://localhost:8002/health || echo "❌ faiss_search no responde"

# Verificar updater
echo "Probando updater (puerto 8001)..."
curl -f http://localhost:8001/health || echo "❌ updater no responde"

# Verificar estadísticas
echo "📊 Estadísticas faiss_search:"
curl -s http://localhost:8002/stats | jq '.'

echo "📊 Estadísticas updater:"
curl -s http://localhost:8001/stats | jq '.'