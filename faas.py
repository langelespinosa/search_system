import json
import time
import requests
from typing import Dict, Any
import logging
from dataclasses import dataclass
from enum import Enum
import random

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventType(Enum):
    AGREGAR = "agregar"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"

@dataclass
class ProductEvent:
    event_type: EventType
    product_id: int
    timestamp: str
    data: Dict[str, Any] = None

class EventQueueProcessor:
    def __init__(self, updater_service_url: str = "http://localhost:8001"):    
        self.updater_url = updater_service_url
        self.is_running = False
        
    def start_processing(self):
        self.is_running = True
        logger.info("🚀 Iniciando procesador de eventos...")
        
        while self.is_running:
            try:
                event = self._read_from_go_queue()
                
                if event:
                    self._process_event(event)
                else:
                    time.sleep(0.1)  # Esperar antes de la siguiente lectura
                    
            except Exception as e:
                logger.error(f"❌ Error procesando eventos: {e}")
                time.sleep(1)
    
    def _read_from_go_queue(self) -> ProductEvent:
        if random.random() < 0.01:  
            event_types = list(EventType)
            return ProductEvent(
                event_type=random.choice(event_types),
                #product_id=random.randint(1, 1000),
                product_id=random.randint(367, 372),
                
                timestamp=str(int(time.time())),
                data={"source": "go_queue"}
            )
        return None
        
    def _process_event(self, event: ProductEvent):
        try:
            endpoint_map = {
                EventType.AGREGAR: f"{self.updater_url}/update/add/{event.product_id}",
                EventType.ACTUALIZAR: f"{self.updater_url}/update/modify/{event.product_id}",
                EventType.ELIMINAR: f"{self.updater_url}/update/delete/{event.product_id}"
            }
            
            url = endpoint_map.get(event.event_type)
            if not url:
                logger.error(f"❌ Tipo de evento no reconocido: {event.event_type}")
                return
            
            # Enviar evento al updater
            response = requests.post(url, 
                                   json={"timestamp": event.timestamp, "data": event.data},
                                   timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Evento {event.event_type.value} para producto {event.product_id} procesado")
            else:
                logger.error(f"❌ Error enviando evento al updater: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error procesando evento {event.product_id}: {e}")
    
    def stop_processing(self):
        self.is_running = False
        logger.info("⏹️ Deteniendo procesador de eventos...")

if __name__ == "__main__":
    processor = EventQueueProcessor()
    try:
        processor.start_processing()
    except KeyboardInterrupt:
        processor.stop_processing()
        logger.info("Servicio detenido")
        