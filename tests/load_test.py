# tests/load_test.py
import requests
import threading
import time
import statistics

class LoadTester:
    def __init__(self):
        self.search_url = "http://localhost:8002"
        self.results = []
        
    def search_worker(self, worker_id, queries, duration):
        """Worker que ejecuta búsquedas por un tiempo determinado"""
        start_time = time.time()
        worker_results = []
        
        while time.time() - start_time < duration:
            query = queries[worker_id % len(queries)]
            
            try:
                start_request = time.time()
                response = requests.get(
                    f"{self.search_url}/search",
                    params={"query": query, "threshold": 0.3},
                    timeout=5
                )
                request_time = time.time() - start_request
                
                if response.status_code == 200:
                    worker_results.append(request_time)
                
            except Exception as e:
                print(f"❌ Worker {worker_id} error: {e}")
            
            time.sleep(0.1)  # Pequeña pausa
        
        self.results.extend(worker_results)
        print(f"✅ Worker {worker_id} completado: {len(worker_results)} requests")
    
    def run_load_test(self, num_workers=5, duration=30):
        """Ejecuta prueba de carga"""
        print(f"🚀 Iniciando prueba de carga:")
        print(f"   Workers: {num_workers}")
        print(f"   Duración: {duration} segundos\n")
        
        queries = [
            "smartphone android",
            "laptop gaming",
            "auriculares bluetooth",
            "memoria 256GB",
            "pantalla AMOLED",
            "procesador intel",
            "gaming RGB",
            "inalámbrico"
        ]
        
        threads = []
        start_time = time.time()
        
        # Crear y ejecutar workers
        for i in range(num_workers):
            thread = threading.Thread(
                target=self.search_worker,
                args=(i, queries, duration)
            )
            threads.append(thread)
            thread.start()
        
        # Esperar a que terminen todos los workers
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Calcular estadísticas
        if self.results:
            total_requests = len(self.results)
            avg_time = statistics.mean(self.results)
            min_time = min(self.results)
            max_time = max(self.results)
            rps = total_requests / total_time
            
            print(f"\n📊 Resultados de la prueba de carga:")
            print(f"   Total requests: {total_requests}")
            print(f"   Requests/segundo: {rps:.2f}")
            print(f"   Tiempo promedio: {avg_time:.3f}s")
            print(f"   Tiempo mínimo: {min_time:.3f}s")
            print(f"   Tiempo máximo: {max_time:.3f}s")
            
            if avg_time < 1.0:
                print("✅ Rendimiento BUENO (< 1s promedio)")
            elif avg_time < 3.0:
                print("⚠️ Rendimiento REGULAR (1-3s promedio)")
            else:
                print("❌ Rendimiento LENTO (> 3s promedio)")
        else:
            print("❌ No se completaron requests exitosos")

if __name__ == "__main__":
    tester = LoadTester()
    tester.run_load_test()