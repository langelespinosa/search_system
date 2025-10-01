# updater.py - Servicio que actualiza archivos .bin y notifica a faiss_search
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import mysql.connector
import uvicorn
from mysql.connector import Error
from typing import Dict, List, Optional
import pickle
import os
from datetime import datetime
import threading
import requests
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',  # Cambiar por host de BD
    'database': 'fireclub_back_pub',
    'user': 'root',
    'password': 'pass'
}

app = FastAPI(title="Updater Service - FAISS Index Manager", version="1.0.0")

class IndexUpdater:
    def __init__(self, search_service_url: str = "http://faiss_search:8002"):
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.dimension = 768
        self.search_service_url = search_service_url
        self.lock = threading.RLock()
        
        # Datos en memoria
        self.productos = {}
        self.corpus = {}
        self.id_to_faiss_idx = {}
        self.faiss_idx_to_id = {}
        self.next_faiss_idx = 0
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Cargar datos existentes
        self._load_current_index()
    
    def _get_db_connection(self):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except Error as e:
            logger.error(f"❌ Error conectando a MySQL: {e}")
            return None
    
    def _obtener_producto_desde_mysql(self, producto_id: int) -> Optional[Dict]:
        connection = self._get_db_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT
                v.id,
                v.id_padre,
                v.activo,
                CASE
                    WHEN v.variante_comb IS NULL OR JSON_LENGTH(v.variante_comb) = 0 THEN NULL
                    ELSE (
                        SELECT GROUP_CONCAT(
                                CASE
                                    WHEN JSON_TYPE(jt.atributo) = 'STRING'
                                    THEN CONCAT(jt.atributo, ' : ', REPLACE(REPLACE(REPLACE(jt.valor_limpio, '["', ''), '"]', ''), '","', ', '))
                                    WHEN JSON_TYPE(jt.atributo) = 'OBJECT'
                                    THEN CONCAT(JSON_UNQUOTE(JSON_EXTRACT(jt.atributo, '$.nombre')), ' : ', REPLACE(REPLACE(REPLACE(jt.valor_limpio, '["', ''), '"]', ''), '","', ', '))
                                    ELSE NULL
                                END
                                SEPARATOR ', '
                            )
                        FROM JSON_TABLE(
                            v.variante_comb,
                            '$[*]' COLUMNS (
                                atributo JSON PATH '$.atributo',
                                valor JSON PATH '$.valor',
                                valor_limpio TEXT PATH '$.valor'
                            )
                        ) jt
                    )
                END AS variante_comb,
                
                p.nombre AS nombre,
                p.descripcion AS descripcion
            FROM tienda_catalogoproductos v
            LEFT JOIN tienda_catalogoproductopadre p
                ON v.id_padre = p.id
            WHERE v.id = %s AND v.activo = '1';
            """
            cursor.execute(query, (producto_id,))
            producto = cursor.fetchone()
            return producto
            
        except Error as e:
            logger.error(f"❌ Error obteniendo producto {producto_id}: {e}")
            return None
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def _crear_texto_producto(self, producto: Dict) -> str:
        nombre = producto.get('nombre', '') or ''
        descripcion = producto.get('descripcion', '') or ''
        variante_comb = producto.get('variante_comb', '') or ''
        return f"{nombre} {descripcion} {variante_comb}".strip()
    
    def _load_current_index(self):
        """Carga el índice actual desde archivos"""
        try:
            if os.path.exists('search_backup.pkl') and os.path.exists('faiss_index.bin'):
                with open('search_backup.pkl', 'rb') as f:
                    backup_data = pickle.load(f)
                
                self.productos = backup_data.get('productos', {})
                self.corpus = backup_data.get('corpus', {})
                self.id_to_faiss_idx = backup_data.get('id_to_faiss_idx', {})
                self.faiss_idx_to_id = backup_data.get('faiss_idx_to_id', {})
                self.next_faiss_idx = backup_data.get('next_faiss_idx', 0)
                
                self.index = faiss.read_index('faiss_index.bin')
                
                logger.info(f"✅ Índice cargado: {len(self.productos)} productos")
            else:
                logger.info("⚠️ No se encontraron archivos de índice existentes")
        except Exception as e:
            logger.error(f"❌ Error cargando índice: {e}")
    
    def _save_index_files(self):
        """Guarda los archivos de índice actualizados"""
        try:
            backup_data = {
                'productos': self.productos,
                'corpus': self.corpus,
                'id_to_faiss_idx': self.id_to_faiss_idx,
                'faiss_idx_to_id': self.faiss_idx_to_id,
                'next_faiss_idx': self.next_faiss_idx,
                'timestamp': datetime.now().isoformat()
            }
            
            # Guardar temporalmente con sufijo
            with open('search_backup_tmp.pkl', 'wb') as f:
                pickle.dump(backup_data, f)
            faiss.write_index(self.index, 'faiss_index_tmp.bin')
            
            # Reemplazar archivos atómicamente
            if os.path.exists('search_backup.pkl'):
                os.replace('search_backup.pkl', 'search_backup_old.pkl')
            if os.path.exists('faiss_index.bin'):
                os.replace('faiss_index.bin', 'faiss_index_old.bin')
            
            os.replace('search_backup_tmp.pkl', 'search_backup.pkl')
            os.replace('faiss_index_tmp.bin', 'faiss_index.bin')
            
            logger.info("💾 Archivos de índice actualizados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando archivos: {e}")
            return False
    
    def _notify_search_service(self, action: str, product_id: int = None):
        """Notifica al servicio de búsqueda sobre cambios en el índice"""
        try:
            url = f"{self.search_service_url}/reload_index"
            data = {"action": action, "product_id": product_id, "timestamp": datetime.now().isoformat()}
            
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Servicio de búsqueda notificado: {action}")
            else:
                logger.warning(f"⚠️ Error notificando servicio de búsqueda: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar al servicio de búsqueda: {e}")
    
    def add_product(self, producto_id: int) -> bool:
        """Agrega un producto al índice"""
        try:
            producto = self._obtener_producto_desde_mysql(producto_id)
            if not producto:
                logger.error(f"❌ Producto {producto_id} no encontrado en BD")
                return False
            
            with self.lock:
                if producto_id in self.productos:
                    logger.info(f"⚠️ Producto {producto_id} ya existe, actualizando...")
                    return self.update_product(producto_id)
                
                # Crear texto y embedding
                texto = self._crear_texto_producto(producto)
                embedding = self.model.encode([texto], normalize_embeddings=True)
                
                # Agregar al índice FAISS
                self.index.add(np.array(embedding, dtype=np.float32))
                
                # Actualizar mapeos
                faiss_idx = self.next_faiss_idx
                self.productos[producto_id] = producto
                self.corpus[producto_id] = texto
                self.id_to_faiss_idx[producto_id] = faiss_idx
                self.faiss_idx_to_id[faiss_idx] = producto_id
                self.next_faiss_idx += 1
                
                # Guardar cambios
                if self._save_index_files():
                    self._notify_search_service("add", producto_id)
                    logger.info(f"✅ Producto {producto_id} agregado exitosamente")
                    return True
                
            return False
        except Exception as e:
            logger.error(f"❌ Error agregando producto {producto_id}: {e}")
            return False
    
    def update_product(self, producto_id: int) -> bool:
        """Actualiza un producto en el índice"""
        try:
            if producto_id not in self.productos:
                logger.info(f"⚠️ Producto {producto_id} no existe, agregando...")
                return self.add_product(producto_id)
            
            producto = self._obtener_producto_desde_mysql(producto_id)
            if not producto:
                logger.info(f"⚠️ Producto {producto_id} no encontrado en BD, eliminando del índice...")
                return self.delete_product(producto_id)
            
            with self.lock:
                # Crear nuevo embedding
                nuevo_texto = self._crear_texto_producto(producto)
                nuevo_embedding = self.model.encode([nuevo_texto], normalize_embeddings=True)
                
                # Actualizar datos
                self.productos[producto_id] = producto
                self.corpus[producto_id] = nuevo_texto
                
                # Reconstruir índice (método simple pero efectivo)
                self._rebuild_index()
                
                if self._save_index_files():
                    self._notify_search_service("update", producto_id)
                    logger.info(f"✅ Producto {producto_id} actualizado exitosamente")
                    return True
                
            return False
        except Exception as e:
            logger.error(f"❌ Error actualizando producto {producto_id}: {e}")
            return False
    
    def delete_product(self, producto_id: int) -> bool:
        """Elimina un producto del índice"""
        try:
            if producto_id not in self.productos:
                logger.warning(f"⚠️ Producto {producto_id} no existe en el índice")
                return True
            
            with self.lock:
                faiss_idx = self.id_to_faiss_idx[producto_id]
                
                # Eliminar de estructuras de datos
                del self.productos[producto_id]
                del self.corpus[producto_id]
                del self.id_to_faiss_idx[producto_id]
                del self.faiss_idx_to_id[faiss_idx]
                
                # Reconstruir índice sin el producto eliminado
                self._rebuild_index()
                
                if self._save_index_files():
                    self._notify_search_service("delete", producto_id)
                    logger.info(f"✅ Producto {producto_id} eliminado exitosamente")
                    return True
                
            return False
        except Exception as e:
            logger.error(f"❌ Error eliminando producto {producto_id}: {e}")
            return False
    
    def _rebuild_index(self):
        """Reconstruye completamente el índice FAISS"""
        if not self.corpus:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_to_faiss_idx.clear()
            self.faiss_idx_to_id.clear()
            self.next_faiss_idx = 0
            return
        
        # Reconstruir mapeos
        new_id_to_faiss = {}
        new_faiss_to_id = {}
        textos_ordenados = []
        
        for idx, (producto_id, texto) in enumerate(self.corpus.items()):
            new_id_to_faiss[producto_id] = idx
            new_faiss_to_id[idx] = producto_id
            textos_ordenados.append(texto)
        
        # Generar embeddings y reconstruir índice
        embeddings = self.model.encode(textos_ordenados, normalize_embeddings=True)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(np.array(embeddings, dtype=np.float32))
        
        # Actualizar mapeos
        self.id_to_faiss_idx = new_id_to_faiss
        self.faiss_idx_to_id = new_faiss_to_id
        self.next_faiss_idx = len(textos_ordenados)

# Instancia del updater
updater = IndexUpdater()

# Endpoints
@app.post("/update/add/{producto_id}")
def add_product_endpoint(producto_id: int):
    try:
        resultado = updater.add_product(producto_id)
        if resultado:
            return JSONResponse(content={"mensaje": f"Producto {producto_id} agregado exitosamente"})
        else:
            raise HTTPException(status_code=404, detail=f"No se pudo agregar producto {producto_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update/modify/{producto_id}")
def update_product_endpoint(producto_id: int):
    try:
        resultado = updater.update_product(producto_id)
        if resultado:
            return JSONResponse(content={"mensaje": f"Producto {producto_id} actualizado exitosamente"})
        else:
            raise HTTPException(status_code=404, detail=f"No se pudo actualizar producto {producto_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update/delete/{producto_id}")
def delete_product_endpoint(producto_id: int):
    try:
        resultado = updater.delete_product(producto_id)
        if resultado:
            return JSONResponse(content={"mensaje": f"Producto {producto_id} eliminado exitosamente"})
        else:
            raise HTTPException(status_code=404, detail=f"No se pudo eliminar producto {producto_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    try:
        with updater.lock:
            stats = {
                "total_productos": len(updater.productos),
                "faiss_total": updater.index.ntotal,
                "next_faiss_idx": updater.next_faiss_idx,
                "dimension": updater.dimension
            }
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "updater"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)