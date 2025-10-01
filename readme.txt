# Levantar servicios
docker-compose up -d

# Esperar 30 segundos para inicialización
sleep 30

# Terminal 1: Servicio de búsqueda
pip install -r requirements.search.txt
python faiss_search.py

# Terminal 2: Servicio updater  
pip install -r requirements.updater.txt
python updater.py

# Terminal 3: Procesador de eventos
pip install -r requirements.faas.txt
python faas.py

# Verificar servicios básicos
curl http://localhost:8002/health
curl http://localhost:8001/health

# Prueba de búsqueda inmediatacurl http://localhost:8002/health
curl "http://localhost:8002/search?query=smartphone&threshold=0.3" | jq
curl http://localhost:8002/health
# Verificar que todo esté funcionando
curl http://localhost:8002/health
curl http://localhost:8001/health

# Buscar productos
curl "http://localhost:8002/search?query=smartphone&threshold=0.3"

# Agregar un producto
curl -X POST http://localhost:8001/update/add/101

# Ver estadísticas
curl http://localhost:8002/stats | jq '.'

# Ejecutar suite de pruebas
python tests/test_api.py
python tests/simulate_events.py
python tests/load_test.py

# Ejecutar el script de pruebas rápidas
chmod +x scripts/quick_test.sh
./scripts/quick_test.sh

# O comandos manuales:
curl -X POST http://localhost:8001/update/add/101
sleep 2
curl "http://localhost:8002/search?query=smartphone&threshold=0.3" | jq '.resultados | length'

# Ejecutar suite completa de pruebas
python tests/test_api.py

# Simulación de eventos
python tests/simulate_events.py

# Verificar que todo funcione
python tests/initial_load.py

# Benchmark completo
chmod +x scripts/performance_benchmark.sh
./scripts/performance_benchmark.sh

# Prueba de carga
python tests/load_test.py


# docker-compose.test.yml
version: '3.8'
services:
  # Servicios principales...
  
  test_runner:
    build: .
    depends_on:
      - faiss_search
      - updater
    volumes:
      - ./tests:/app/tests
    command: python tests/test_api.py