#!/bin/bash
# scripts/full_system_test.sh - Prueba completa del sistema

echo "🧪 INICIANDO PRUEBA COMPLETA DEL SISTEMA"
echo "======================================="

# Función para esperar que un servicio esté listo
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    echo "Esperando que $name esté listo..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "✅ $name está listo"
            return 0
        fi
        
        echo "⏳ Intento $attempt/$max_attempts para $name..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $name no respondió después de $max_attempts intentos"
    return 1
}

# 1. Verificar que Docker Compose esté corriendo
echo -e "\n🐳 Verificando contenedores Docker..."
if ! docker-compose ps | grep -q "Up"; then
    echo "🚀 Iniciando contenedores..."
    docker-compose up -d
    sleep 10
fi

# 2. Esperar que los servicios estén listos
echo -e "\n⏳ Esperando servicios..."
wait_for_service "http://localhost:8002/health" "Search Service"
wait_for_service "http://localhost:8001/health" "Updater Service"

# 3. Ejecutar carga inicial
echo -e "\n📥 Ejecutando carga inicial..."
python3 << EOF
import requests
import time

updater_url = "http://localhost:8001"
productos_test = [101, 102, 103, 104]

print("Agregando productos de prueba...")
for producto_id in productos_test:
    try:
        response = requests.post(f"{updater_url}/update/add/{producto_id}", timeout=10)
        status = "✅" if response.status_code == 200 else "⚠️"
        print(f"  {status} Producto {producto_id}")
    except Exception as e:
        print(f"  ❌ Error con producto {producto_id}: {e}")
    time.sleep(1)

print("⏳ Esperando procesamiento...")
time.sleep(5)

# Verificar carga
try:
    stats = requests.get("http://localhost:8002/stats").json()
    print(f"📊 Productos cargados: {stats['total_productos']}")
except:
    print("❌ Error verificando carga")
EOF

# 4. Ejecutar suite de pruebas
echo -e "\n🔍 Ejecutando pruebas de API..."
python3 << EOF
import requests
import threading
import time

def test_concurrent_searches():
    search_url = "http://localhost:8002"
    queries = ["smartphone", "laptop", "auriculares", "gaming", "bluetooth"]
    results = []
    
    def worker(query, worker_id):
        try:
            start_time = time.time()
            response = requests.get(f"{search_url}/search", 
                                  params={"query": query, "threshold": 0.3}, 
                                  timeout=5)
            request_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                results.append((worker_id, len(data.get('resultados', [])), request_time))
                print(f"✅ Worker {worker_id} ({query}): {len(data.get('resultados', []))} resultados en {request_time:.3f}s")
            else:
                print(f"❌ Worker {worker_id}: Error {response.status_code}")
        except Exception as e:
            print(f"❌ Worker {worker_id}: {e}")
    
    print("🔀 Probando búsquedas concurrentes...")
    threads = []
    
    for i, query in enumerate(queries):
        thread = threading.Thread(target=worker, args=(query, i+1))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    if results:
        avg_time = sum(r[2] for r in results) / len(results)
        total_results = sum(r[1] for r in results)
        print(f"📊 Promedio: {avg_time:.3f}s, Total resultados: {total_results}")
        return True
    return False

def test_crud_operations():
    updater_url = "http://localhost:8001"
    search_url = "http://localhost:8002"
    
    print("⚙️ Probando operaciones CRUD...")
    
    # Test update
    try:
        response = requests.post(f"{updater_url}/update/modify/101", timeout=10)
        if response.status_code == 200:
            print("✅ Actualización: OK")
        else:
            print(f"⚠️ Actualización: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en actualización: {e}")
    
    time.sleep(3)
    
    # Test delete and re-add
    try:
        # Delete
        response = requests.post(f"{updater_url}/update/delete/102", timeout=10)
        print(f"🗑️ Eliminar 102: {'OK' if response.status_code == 200 else 'Error'}")
        
        time.sleep(2)
        
        # Check stats
        stats = requests.get(f"{search_url}/stats").json()
        print(f"📊 Productos después de eliminar: {stats['total_productos']}")
        
        time.sleep(1)
        
        # Re-add
        response = requests.post(f"{updater_url}/update/add/102", timeout=10)
        print(f"➕ Re-agregar 102: {'OK' if response.status_code == 200 else 'Error'}")
        
        time.sleep(2)
        
        # Final stats
        stats = requests.get(f"{search_url}/stats").json()
        print(f"📊 Productos después de re-agregar: {stats['total_productos']}")
        
    except Exception as e:
        print(f"❌ Error en operaciones CRUD: {e}")

# Ejecutar pruebas
print("🧪 Iniciando pruebas de funcionalidad...")
test_concurrent_searches()
test_crud_operations()
EOF

# 5. Prueba de estrés básica
echo -e "\n💪 Ejecutando prueba de estrés..."
python3 << EOF
import requests
import threading
import time
import statistics

def stress_test():
    search_url = "http://localhost:8002"
    queries = ["smartphone android", "laptop gaming", "auriculares bluetooth", 
               "memoria 256GB", "pantalla AMOLED", "gaming RGB"]
    
    results = []
    errors = 0
    
    def stress_worker(worker_id, duration=15):
        nonlocal errors
        start_time = time.time()
        worker_results = []
        
        while time.time() - start_time < duration:
            query = queries[worker_id % len(queries)]
            try:
                request_start = time.time()
                response = requests.get(f"{search_url}/search",
                                      params={"query": query, "threshold": 0.3},
                                      timeout=3)
                request_time = time.time() - request_start
                
                if response.status_code == 200:
                    worker_results.append(request_time)
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
            
            time.sleep(0.05)  # 50ms entre requests
        
        results.extend(worker_results)
        print(f"✅ Stress worker {worker_id}: {len(worker_results)} requests exitosos")
    
    print("🔥 Iniciando prueba de estrés (15s, 8 workers)...")
    threads = []
    start_time = time.time()
    
    for i in range(8):
        thread = threading.Thread(target=stress_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    if results:
        total_requests = len(results)
        avg_time = statistics.mean(results)
        rps = total_requests / total_time
        
        print(f"📊 Resultados de estrés:")
        print(f"   Total requests exitosos: {total_requests}")
        print(f"   Requests con error: {errors}")
        print(f"   RPS promedio: {rps:.2f}")
        print(f"   Tiempo promedio: {avg_time:.3f}s")
        print(f"   Tiempo máximo: {max(results):.3f}s")
        
        if avg_time < 0.5 and errors < total_requests * 0.05:
            print("✅ Sistema pasó la prueba de estrés")
        else:
            print("⚠️ Sistema mostró signos de estrés")
    else:
        print("❌ No se completaron requests en la prueba de estrés")

stress_test()
EOF

# 6. Verificar logs y estado final
echo -e "\n📝 Verificando logs recientes..."
echo "Logs del Search Service:"
docker-compose logs --tail=10 faiss_search

echo -e "\nLogs del Updater Service:"  
docker-compose logs --tail=10 updater

# 7. Estado final del sistema
echo -e "\n📊 Estado final del sistema:"
final_search_stats=$(curl -s "http://localhost:8002/stats")
final_updater_stats=$(curl -s "http://localhost:8001/stats")

echo "Search Service:"
echo "$final_search_stats" | jq .

echo -e "\nUpdater Service:"
echo "$final_updater_stats" | jq .

# 8. Prueba de recuperación
echo -e "\n🔄 Probando recuperación del sistema..."
echo "Reiniciando servicio de búsqueda..."
docker-compose restart faiss_search

sleep 5

if curl -s -f "http://localhost:8002/health" > /dev/null; then
    echo "✅ Servicio de búsqueda se recuperó correctamente"
    
    # Verificar que los datos persisten
    recovery_stats=$(curl -s "http://localhost:8002/stats")
    productos_recovery=$(echo "$recovery_stats" | jq '.total_productos')
    echo "📊 Productos después de reinicio: $productos_recovery"
    
    if [ "$productos_recovery" -gt 0 ]; then
        echo "✅ Datos persistieron correctamente"
    else
        echo "❌ Se perdieron datos en el reinicio"
    fi
else
    echo "❌ Servicio de búsqueda no se recuperó"
fi

echo -e "\n🎉 PRUEBA COMPLETA DEL SISTEMA FINALIZADA"
echo "======================================="
