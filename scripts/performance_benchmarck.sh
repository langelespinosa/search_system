#!/bin/bash
# scripts/performance_benchmark.sh - Benchmark de rendimiento

echo "⚡ BENCHMARK DE RENDIMIENTO"
echo "=========================="

# Verificar dependencias
command -v curl >/dev/null 2>&1 || { echo "❌ curl requerido"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ jq requerido"; exit 1; }

# URLs de servicios
SEARCH_URL="http://localhost:8002"
UPDATER_URL="http://localhost:8001"

# Queries para benchmark
QUERIES=(
    "smartphone android samsung"
    "laptop gaming intel nvidia"
    "auriculares bluetooth sony"
    "memoria RAM 16GB DDR4"
    "pantalla AMOLED 120Hz"
    "procesador intel i7"
    "tarjeta gráfica RTX"
    "almacenamiento SSD 1TB"
    "cámara 108MP ultra wide"
    "batería 5000mAh carga rápida"
)

# Función para benchmark de latencia
benchmark_latency() {
    echo "🚀 Benchmark de latencia individual..."
    
    local total_time=0
    local successful_requests=0
    local failed_requests=0
    
    for query in "${QUERIES[@]}"; do
        echo -n "  Probando: '$query'... "
        
        local start_time=$(date +%s.%3N)
        local response=$(curl -s -w "%{http_code}" -o /tmp/benchmark_response.json \
                        "$SEARCH_URL/search?query=$(echo $query | sed 's/ /%20/g')&threshold=0.3")
        local end_time=$(date +%s.%3N)
        
        local request_time=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response" = "200" ]; then
            local results_count=$(jq '.resultados | length' /tmp/benchmark_response.json 2>/dev/null || echo "0")
            echo "${request_time}s (${results_count} resultados)"
            total_time=$(echo "$total_time + $request_time" | bc)
            ((successful_requests++))
        else
            echo "ERROR ($response)"
            ((failed_requests++))
        fi
    done
    
    if [ $successful_requests -gt 0 ]; then
        local avg_latency=$(echo "scale=3; $total_time / $successful_requests" | bc)
        echo ""
        echo "📊 Resultados de latencia:"
        echo "  ✅ Requests exitosos: $successful_requests"
        echo "  ❌ Requests fallidos: $failed_requests"
        echo "  ⏱️ Latencia promedio: ${avg_latency}s"
        
        if (( $(echo "$avg_latency < 0.5" | bc -l) )); then
            echo "  🏆 EXCELENTE (< 0.5s)"
        elif (( $(echo "$avg_latency < 1.0" | bc -l) )); then
            echo "  ✅ BUENO (0.5-1.0s)"
        elif (( $(echo "$avg_latency < 2.0" | bc -l) )); then
            echo "  ⚠️ REGULAR (1.0-2.0s)"
        else
            echo "  ❌ LENTO (> 2.0s)"
        fi
    fi
    
    rm -f /tmp/benchmark_response.json
}

# Función para benchmark de throughput
benchmark_throughput() {
    echo -e "\n🔥 Benchmark de throughput (carga concurrente)..."
    
    local duration=30
    local concurrent_users=10
    
    echo "  Configuración: $concurrent_users usuarios durante ${duration}s"
    
    python3 << EOF
import requests
import threading
import time
import statistics
import random

search_url = "$SEARCH_URL"
queries = [$(printf '"%s",' "${QUERIES[@]}" | sed 's/,$//')]
duration = $duration
num_workers = $concurrent_users

results = []
errors = 0
lock = threading.Lock()

def worker(worker_id):
    global errors
    start_time = time.time()
    worker_results = []
    
    while time.time() - start_time < duration:
        query = random.choice(queries)
        try:
            request_start = time.time()
            response = requests.get(f"{search_url}/search",
                                  params={"query": query, "threshold": 0.3},
                                  timeout=5)
            request_time = time.time() - request_start
            
            with lock:
                if response.status_code == 200:
                    results.append(request_time)
                else:
                    errors += 1
                    
        except Exception as e:
            with lock:
                errors += 1
        
        time.sleep(0.01)  # 10ms pausa
    
    print(f"  Worker {worker_id:2d}: {len(worker_results)} requests locales")

print(f"  Iniciando {num_workers} workers...")
threads = []
start_time = time.time()

for i in range(num_workers):
    thread = threading.Thread(target=worker, args=(i+1,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

total_time = time.time() - start_time
total_requests = len(results)

if results:
    avg_latency = statistics.mean(results)
    p95_latency = statistics.quantiles(results, n=20)[18] if len(results) >= 20 else max(results)
    throughput = total_requests / total_time
    
    print(f"\n📊 Resultados de throughput:")
    print(f"  📈 Total requests: {total_requests}")
    print(f"  ❌ Requests fallidos: {errors}")
    print(f"  🚀 Throughput: {throughput:.2f} RPS")
    print(f"  ⏱️ Latencia promedio: {avg_latency:.3f}s")
    print(f"  📊 Latencia P95: {p95_latency:.3f}s")
    print(f"  ✅ Tasa de éxito: {(total_requests/(total_requests+errors)*100):.1f}%")
    
    if throughput > 50 and avg_latency < 1.0:
        print("  🏆 EXCELENTE rendimiento")
    elif throughput > 20 and avg_latency < 2.0:
        print("  ✅ BUEN rendimiento")
    elif throughput > 10:
        print("  ⚠️ REGULAR rendimiento")
    else:
        print("  ❌ BAJO rendimiento")
else:
    print("  ❌ No se completaron requests exitosos")
EOF
}

# Función para benchmark de operaciones CRUD
benchmark_crud() {
    echo -e "\n⚙️ Benchmark de operaciones CRUD..."
    
    local test_products=(201 202 203 204 205)
    
    echo "  Probando operaciones de actualización del índice..."
    
    local total_crud_time=0
    local crud_operations=0
    
    for product_id in "${test_products[@]}"; do
        # Add operation
        echo -n "    ADD $product_id... "
        local start_time=$(date +%s.%3N)
        local response=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$UPDATER_URL/update/add/$product_id")
        local end_time=$(date +%s.%3N)
        local operation_time=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response" = "200" ]; then
            echo "${operation_time}s"
            total_crud_time=$(echo "$total_crud_time + $operation_time" | bc)
            ((crud_operations++))
        else
            echo "ERROR ($response)"
        fi
        
        sleep 1
        
        # Update operation
        echo -n "    UPDATE $product_id... "
        start_time=$(date +%s.%3N)
        response=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$UPDATER_URL/update/modify/$product_id")
        end_time=$(date +%s.%3N)
        operation_time=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response" = "200" ]; then
            echo "${operation_time}s"
            total_crud_time=$(echo "$total_crud_time + $operation_time" | bc)
            ((crud_operations++))
        else
            echo "ERROR ($response)"
        fi
        
        sleep 1
    done
    
    if [ $crud_operations -gt 0 ]; then
        local avg_crud_time=$(echo "scale=3; $total_crud_time / $crud_operations" | bc)
        echo ""
        echo "📊 Resultados CRUD:"
        echo "  ⚙️ Operaciones exitosas: $crud_operations"
        echo "  ⏱️ Tiempo promedio: ${avg_crud_time}s"
        
        if (( $(echo "$avg_crud_time < 2.0" | bc -l) )); then
            echo "  🏆 EXCELENTE velocidad de actualización"
        elif (( $(echo "$avg_crud_time < 5.0" | bc -l) )); then
            echo "  ✅ BUENA velocidad de actualización"
        else
            echo "  ⚠️ LENTA velocidad de actualización"
        fi
    fi
}

# Ejecutar benchmarks
echo "Iniciando benchmark completo..."
echo ""

# Verificar que los servicios estén activos
if ! curl -s -f "$SEARCH_URL/health" >/dev/null; then
    echo "❌ Search service no está disponible en $SEARCH_URL"
    exit 1
fi

if ! curl -s -f "$UPDATER_URL/health" >/dev/null; then
    echo "❌ Updater service no está disponible en $UPDATER_URL"
    exit 1
fi

echo "✅ Servicios verificados, iniciando benchmarks..."
echo ""

# Ejecutar cada benchmark
benchmark_latency
benchmark_throughput  
benchmark_crud

echo -e "\n🎉 BENCHMARK COMPLETADO"
echo "======================="