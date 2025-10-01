# tests/test_api.py
import requests
import json
import time

class SearchAPITester:
    def __init__(self):
        self.search_url = "http://localhost:8002"
        self.updater_url = "http://localhost:8001"
    
    def test_search_queries(self):
        """Prueba diferentes tipos de búsquedas"""
        
        queries = [
            ("smartphone", "Búsqueda básica de smartphone"),
            ("gaming laptop", "Búsqueda de laptop gaming"),
            ("auriculares bluetooth", "Búsqueda de auriculares"),
            ("negro", "Búsqueda por color"),
            ("16GB", "Búsqueda por especificación"),
            ("AMOLED", "Búsqueda por característica técnica")
        ]
        
        print("🔍 Ejecutando pruebas de búsqueda...")
        
        for query, description in queries:
            try:
                response = requests.get(
                    f"{self.search_url}/search",
                    params={"query": query, "threshold": 0.3},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    resultados = len(data.get('resultados', []))
                    print(f"✅ {description}: {resultados} resultados")
                    
                    # Mostrar primer resultado si existe
                    if resultados > 0:
                        primer_resultado = data['resultados'][0]
                        print(f"   Top: {primer_resultado['nombre']} (similitud: {primer_resultado['similitud']})")
                else:
                    print(f"❌ {description}: Error {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {description}: {e}")
            
            time.sleep(0.5)  # Pausa entre consultas
    
    def test_product_operations(self):
        """Prueba operaciones CRUD de productos"""
        
        test_product_id = 999
        
        print("⚙️ Ejecutando pruebas de operaciones...")
        
        # 1. Agregar producto (simulado, no existe en BD)
        try:
            response = requests.post(f"{self.updater_url}/update/add/{test_product_id}")
            print(f"🔄 Agregar producto {test_product_id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error agregando: {e}")
        
        time.sleep(2)
        
        # 2. Actualizar producto existente
        existing_id = 101
        try:
            response = requests.post(f"{self.updater_url}/update/modify/{existing_id}")
            if response.status_code == 200:
                print(f"✅ Actualizar producto {existing_id}: OK")
            else:
                print(f"⚠️ Actualizar producto {existing_id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error actualizando: {e}")
        
        time.sleep(2)
        
        # 3. Eliminar producto
        try:
            response = requests.post(f"{self.updater_url}/update/delete/{existing_id}")
            if response.status_code == 200:
                print(f"✅ Eliminar producto {existing_id}: OK")
            else:
                print(f"⚠️ Eliminar producto {existing_id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error eliminando: {e}")
        
        time.sleep(2)
        
        # 4. Volver a agregar
        try:
            response = requests.post(f"{self.updater_url}/update/add/{existing_id}")
            if response.status_code == 200:
                print(f"✅ Re-agregar producto {existing_id}: OK")
        except Exception as e:
            print(f"❌ Error re-agregando: {e}")
    
    def test_concurrent_searches(self):
        """Prueba búsquedas concurrentes"""
        import threading
        
        def search_worker(query, worker_id):
            try:
                response = requests.get(
                    f"{self.search_url}/search",
                    params={"query": query, "threshold": 0.3},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Worker {worker_id}: {len(data.get('resultados', []))} resultados")
                else:
                    print(f"❌ Worker {worker_id}: Error {response.status_code}")
            except Exception as e:
                print(f"❌ Worker {worker_id}: {e}")
        
        print("🔀 Ejecutando pruebas concurrentes...")
        
        queries = ["smartphone", "laptop", "auriculares", "gaming", "bluetooth"]
        threads = []
        
        for i, query in enumerate(queries):
            thread = threading.Thread(target=search_worker, args=(query, i+1))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        print("🚀 Iniciando suite completa de pruebas...\n")
        
        self.test_search_queries()
        print()
        
        self.test_product_operations()
        print()
        
        self.test_concurrent_searches()
        print()
        
        print("🎉 Pruebas completadas!")

if __name__ == "__main__":
    tester = SearchAPITester()
    tester.run_all_tests()