#!/bin/bash
# scripts/quick_test.sh - Script para pruebas rápidas

echo "🚀 INICIANDO PRUEBAS RÁPIDAS DEL SISTEMA"
echo "========================================"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar respuesta
check_response() {
    local url=$1
    local name=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✅ $name: OK${NC}"
        return 0
    else
        echo -e "${RED}❌ $name: Error ($response)${NC}"
        return 1
    fi
}

# Función para verificar JSON response
check_json_response() {
    local url=$1
    local name=$2
    local response=$(curl -s "$url")
    
    if echo "$response" | jq . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name: JSON válido${NC}"
        echo "$response" | jq .
        return 0
    else
        echo -e "${RED}❌ $name: JSON inválido${NC}"
        echo "$response"
        return 1
    fi
}

# 1. Verificar servicios básicos
echo -e "\n${YELLOW}📡 Verificando servicios básicos...${NC}"
check_response "http://localhost:8002/health" "Search Service"
check_response "http://localhost:8001/health" "Updater Service"

# 2. Verificar estadísticas
echo -e "\n${YELLOW}📊 Verificando estadísticas...${NC}"
check_json_response "http://localhost:8002/stats" "Search Stats"
check_json_response "http://localhost:8001/stats" "Updater Stats"

# 3. Pruebas de búsqueda básicas
echo -e "\n${YELLOW}🔍 Probando búsquedas...${NC}"

queries=("smartphone" "laptop" "auriculares" "gaming" "bluetooth")

for query in "${queries[@]}"; do
    url="http://localhost:8002/search?query=${query}&threshold=0.3"
    response=$(curl -s "$url")
    
    if echo "$response" | jq . > /dev/null 2>&1; then
        resultados=$(echo "$response" | jq '.resultados | length')
        echo -e "${GREEN}✅ Búsqueda '$query': $resultados resultados${NC}"
    else
        echo -e "${RED}❌ Búsqueda '$query': Error${NC}"
    fi
done

# 4. Prueba de operaciones CRUD
echo -e "\n${YELLOW}⚙️ Probando operaciones CRUD...${NC}"

# Agregar producto
echo "Agregando producto 101..."
add_response=$(curl -s -X POST http://localhost:8001/update/add/101)
if echo "$add_response" | grep -q "exitosamente"; then
    echo -e "${GREEN}✅ Agregar: OK${NC}"
else
    echo -e "${YELLOW}⚠️ Agregar: $add_response${NC}"
fi

sleep 2

# Actualizar producto
echo "Actualizando producto 101..."
update_response=$(curl -s -X POST http://localhost:8001/update/modify/101)
if echo "$update_response" | grep -q "exitosamente"; then
    echo -e "${GREEN}✅ Actualizar: OK${NC}"
else
    echo -e "${YELLOW}⚠️ Actualizar: $update_response${NC}"
fi

sleep 2

# 5. Verificar que el índice se actualizó
echo -e "\n${YELLOW}🔄 Verificando actualización de índice...${NC}"
final_stats=$(curl -s "http://localhost:8002/stats")
total_productos=$(echo "$final_stats" | jq '.total_productos')
echo "Total productos en índice: $total_productos"

# 6. Prueba de búsqueda después de cambios
echo -e "\n${YELLOW}🔍 Búsqueda después de cambios...${NC}"
search_after=$(curl -s "http://localhost:8002/search?query=smartphone&threshold=0.1")
resultados_after=$(echo "$search_after" | jq '.resultados | length')
echo -e "${GREEN}✅ Resultados después de cambios: $resultados_after${NC}"

echo -e "\n${GREEN}🎉 PRUEBAS RÁPIDAS COMPLETADAS${NC}"
echo "========================================"