# tests/simulate_events.py
import requests
import random
import time
import json

class EventSimulator:
    def __init__(self):
        self.updater_url = "http://localhost:8001"
        self.product_ids = [101, 102, 103, 104]
    
    def simulate_add_events(self, count=5):
        """Simula eventos de agregar productos"""
        print(f"➕ Simulando {count} eventos de agregar...")
        
        for i in range(count):
            product_id = random.choice(self.product_ids)
            try:
                response = requests.post(f"{self.updater_url}/update/add/{product_id}")
                status = "✅" if response.status_code == 200 else "⚠️"
                print(f"  {status} Agregar producto {product_id}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            time.sleep(1)
    
    def simulate_update_events(self, count=3):
        """Simula eventos de actualizar productos"""
        print(f"🔄 Simulando {count} eventos de actualizar...")
        
        for i in range(count):
            product_id = random.choice(self.product_ids)
            try:
                response = requests.post(f"{self.updater_url}/update/modify/{product_id}")
                status = "✅" if response.status_code == 200 else "⚠️"
                print(f"  {status} Actualizar producto {product_id}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            time.sleep(2)
    
    def simulate_delete_events(self, count=2):
        """Simula eventos de eliminar productos"""
        print(f"🗑️ Simulando {count} eventos de eliminar...")
        
        for i in range(count):
            product_id = random.choice(self.product_ids)
            try:
                response = requests.post(f"{self.updater_url}/update/delete/{product_id}")
                status = "✅" if response.status_code == 200 else "⚠️"
                print(f"  {status} Eliminar producto {product_id}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            time.sleep(1)
    
    def run_simulation(self):
        """Ejecuta una simulación completa"""
        print("🎭 Iniciando simulación de eventos...\n")
        
        # Verificar estado inicial
        try:
            response = requests.get("http://localhost:8002/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"📊 Estado inicial: {stats['total_productos']} productos\n")
        except:
            print("⚠️ No se pudo obtener estado inicial\n")
        
        # Ejecutar simulación
        self.simulate_add_events()
        time.sleep(3)
        
        self.simulate_update_events()
        time.sleep(3)
        
        self.simulate_delete_events()
        time.sleep(3)
        
        # Verificar estado final
        try:
            response = requests.get("http://localhost:8002/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"\n📊 Estado final: {stats['total_productos']} productos")
        except:
            print("\n⚠️ No se pudo obtener estado final")
        
        print("\n🎉 Simulación completada!")

if __name__ == "__main__":
    simulator = EventSimulator()
    simulator.run_simulation()