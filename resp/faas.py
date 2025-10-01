import json
import time
import requests
from typing import Dict, Any
import logging
from dataclasses import dataclass
from enum import Enum

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
    def __init__(self, updater_service_url: str = "http://updater:8001"):
        self.updater_url = updater_service_url
        self.is_running = False
        
    def start_processing(self):
        """Inicia el procesamiento de eventos de la cola"""
        self.is_running = True
        logger.info("🚀 Iniciando procesador de eventos...")
        
        while self.is_running:
            try:
                #
                # Simular lectura de cola Go (reemplazar con cliente real)
                #
                event = self._read_from_go_queue()
                
                if event:
                    self._process_event(event)
                else:
                    time.sleep(0.1)  # Esperar antes de la siguiente lectura
                    
            except Exception as e:
                logger.error(f"❌ Error procesando eventos: {e}")
                time.sleep(1)
    
    def _read_from_go_queue(self) -> ProductEvent:
        """
        Simula la lectura de una cola de eventos Go
        Reemplazar con la implementación real del cliente de cola
        """
        # EJEMPLO: Aquí iría la lógica real para leer de la cola Go
        # Por ejemplo: usando un cliente de RabbitMQ, Kafka, Redis, etc.
        
        # Simulación para demostrar el concepto:
        import random
        if random.random() < 0.01:  # 1% probabilidad de evento
            event_types = list(EventType)
            return ProductEvent(
                event_type=random.choice(event_types),
                #product_id=random.randint(1, 1000),
                product_id=random.randint(1, 1367),
                
                timestamp=str(int(time.time())),
                data={"source": "go_queue"}
            )
        return None
        
        # Implementación real sería algo como:
        # try:
        #     message = queue_client.consume(timeout=100)
        #     if message:
        #         return ProductEvent(**json.loads(message.body))
        # except Exception as e:
        #     logger.error(f"Error leyendo cola: {e}")
        # return None

    def _process_event(self, event: ProductEvent):
        """Procesa un evento enviándolo al servicio updater"""
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
        """Detiene el procesamiento de eventos"""
        self.is_running = False
        logger.info("⏹️ Deteniendo procesador de eventos...")

# Para uso con queue real, ejemplo con RabbitMQ:
"""
import pika
import json

class RabbitMQEventProcessor(EventQueueProcessor):
    def __init__(self, updater_service_url: str = "http://updater:8001", 
                 rabbitmq_url: str = "amqp://localhost", 
                 queue_name: str = "product_events"):
        super().__init__(updater_service_url)
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    def _setup_connection(self):
        self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)
    
    def _read_from_go_queue(self) -> ProductEvent:
        try:
            if not self.connection or self.connection.is_closed:
                self._setup_connection()
            
            method, properties, body = self.channel.basic_get(queue=self.queue_name)
            if method:
                data = json.loads(body)
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
                return ProductEvent(**data)
            return None
        except Exception as e:
            logger.error(f"Error leyendo de RabbitMQ: {e}")
            return None
"""

if __name__ == "__main__":
    processor = EventQueueProcessor()
    try:
        processor.start_processing()
    except KeyboardInterrupt:
        processor.stop_processing()
        logger.info("👋 Servicio detenido")
        