#!/bin/bash  
# scripts/monitor_system.sh - Monitoreo en tiempo real

echo "📊 MONITOR DEL SISTEMA EN TIEMPO REAL"
echo "===================================="
echo "Presiona Ctrl+C para salir"
echo ""

# Función para obtener estadísticas
get_stats() {
    local search_stats=$(curl -s "http://localhost:8002/stats" 2>/dev/null)
    local updater_stats=$(curl -s "http://localhost:8001/stats" 2>/dev/null)
    local search_health=$(curl -s "http://localhost:8002/health" 2>/dev/null)
    local updater_health=$(curl -s "http://localhost:8001/health" 2>/dev/null)
    
    # Limpiar pantalla
    clear
    
    echo "📊 MONITOR DEL SISTEMA - $(date)"
    echo "================================"
    echo ""
    
    # Estado de servicios
    echo "🟢 ESTADO DE SERVICIOS:"
    if echo "$search_health" | grep -q "healthy" 2>/dev/null; then
        echo "  ✅ Search Service: ACTIVO"
    else
        echo "  ❌ Search Service: INACTIVO"
    fi
    
    if echo "$updater_health" | grep -q "healthy" 2>/dev/null; then
        echo "  ✅ Updater Service: ACTIVO"
    else
        echo "  ❌ Updater Service: INACTIVO"
    fi
    
    echo ""
    
    # Estadísticas del Search Service
    echo "🔍 SEARCH SERVICE:"
    if [ ! -z "$search_stats" ]; then
        local total_productos=$(echo "$search_stats" | jq -r '.total_productos // "N/A"')
        local faiss_total=$(echo "$search_stats" | jq -r '.faiss_total // "N/A"')
        local index_loaded=$(echo "$search_stats" | jq -r '.index_loaded // "N/A"')
        
        echo "  📦 Total productos: $total_productos"
        echo "  🔢 Índice FAISS: $faiss_total vectores"
        echo "  💾 Índice cargado: $index_loaded"
    else
        echo "  ❌ No se pudo obtener estadísticas"
    fi
    
    echo ""
    
    # Estadísticas del Updater Service
    echo "⚙️ UPDATER SERVICE:"
    if [ ! -z "$updater_stats" ]; then
        local updater_productos=$(echo "$updater_stats" | jq -r '.total_productos // "N/A"')
        local updater_faiss=$(echo "$updater_stats" | jq -r '.faiss_total // "N/A"')
        
        echo "  📦 Total productos: $updater_productos"
        echo "  🔢 Índice FAISS: $updater_faiss vectores"
    else
        echo "  ❌ No se pudo obtener estadísticas"
    fi
    
    echo ""
    
    # Estado de contenedores Docker
    echo "🐳 CONTENEDORES DOCKER:"
    docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Ports}}" 2>/dev/null || echo "  ❌ Docker Compose no disponible"
    
    echo ""
    
    # Uso de recursos (si está disponible)
    if command -v docker &> /dev/null; then
        echo "💻 USO DE RECURSOS:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker-compose ps -q 2>/dev/null) 2>/dev/null | head -10 || echo "  ❌ Estadísticas no disponibles"
    fi
    
    echo ""
    echo "🔄 Actualizando cada 5 segundos... (Ctrl+C para salir)"
}

# Trap para limpiar al salir
trap 'echo -e "\n👋 Monitor finalizado"; exit 0' INT

# Loop principal
while true; do
    get_stats
    sleep 5
done