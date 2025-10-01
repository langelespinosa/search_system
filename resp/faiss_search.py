# faiss_search.py - Servicio de búsqueda que nunca se detiene
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import re
import warnings
import uvicorn
from typing import Dict, List, Tuple, Optional
import threading
import pickle
import os
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)

app = FastAPI(title="FAISS Search Service - Búsqueda Semántica", version="1.0.0")

class SearchService:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.dimension = 768
        
        # Índice activo (para búsquedas)
        self.active_index = None
        self.active_productos = {}
        self.active_corpus = {}
        self.active_id_to_faiss_idx = {}
        self.active_faiss_idx_to_id = {}
        
        # Índice en carga (para actualizaciones sin interrumpir búsquedas)
        self.loading_index = None
        self.loading_productos = {}
        self.loading_corpus = {}
        self.loading_id_to_faiss_idx = {}
        self.loading_faiss_idx_to_id = {}
        
        self.search_lock = threading.RLock()  # Para búsquedas
        self.reload_lock = threading.RLock()  # Para recarga de índice
        
        # Cargar índice inicial
        self._load_index()
    
    def _load_index(self):
        """Carga el índice desde archivos"""
        try:
            if os.path.exists('search_backup.pkl') and os.path.exists('faiss_index.bin'):
                with open('search_backup.pkl', 'rb') as f:
                    backup_data = pickle.load(f)
                
                with self.reload_lock:
                    # Cargar en estructuras de loading
                    self.loading_productos = backup_data.get('productos', {})
                    self.loading_corpus = backup_data.get('corpus', {})
                    self.loading_id_to_faiss_idx = backup_data.get('id_to_faiss_idx', {})
                    self.loading_faiss_idx_to_id = backup_data.get('faiss_idx_to_id', {})
                    
                    self.loading_index = faiss.read_index('faiss_index.bin')
                    
                    # Hacer swap atómico
                    self._atomic_swap()
                    
                    timestamp = backup_data.get('timestamp', 'desconocido')
                    logger.info(f"✅ Índice cargado exitosamente (creado: {timestamp})")
                    logger.info(f"📊 {len(self.active_productos)} productos disponibles")
            else:
                logger.warning("⚠️ No se encontraron archivos de índice")
                # Crear índice vacío
                self.active_index = faiss.IndexFlatIP(self.dimension)
                
        except Exception as e:
            logger.error(f"❌ Error cargando índice: {e}")
            # Crear índice vacío como fallback
            self.active_index = faiss.IndexFlatIP(self.dimension)
    
    def _atomic_swap(self):
        #Intercambia el índice activo de forma atómica
        with self.search_lock:
            # Intercambiar todos los elementos de una vez
            self.active_index = self.loading_index
            self.active_productos = self.loading_productos
            self.active_corpus = self.loading_corpus
            self.active_id_to_faiss_idx = self.loading_id_to_faiss_idx
            self.active_faiss_idx_to_id = self.loading_faiss_idx_to_id
            
            # Limpiar loading structures
            self.loading_index = None
            self.loading_productos = {}
            self.loading_corpus = {}
            self.loading_id_to_faiss_idx = {}
            self.loading_faiss_idx_to_id = {}
            
            logger.info("🔄 Swap de índice completado")
    
    def reload_index_from_files(self):
        #Recarga el índice desde archivos sin interrumpir búsquedas"""
        try:
            if not os.path.exists('search_backup.pkl') or not os.path.exists('faiss_index.bin'):
                logger.warning("⚠️ Archivos de índice no encontrados para recarga")
                return False
            
            with self.reload_lock:
                # Cargar en estructuras temporales
                with open('search_backup.pkl', 'rb') as f:
                    backup_data = pickle.load(f)
                
                self.loading_productos = backup_data.get('productos', {})
                self.loading_corpus = backup_data.get('corpus', {})
                self.loading_id_to_faiss_idx = backup_data.get('id_to_faiss_idx', {})
                self.loading_faiss_idx_to_id = backup_data.get('faiss_idx_to_id', {})
                
                self.loading_index = faiss.read_index('faiss_index.bin')
                
                # Swap atómico
                self._atomic_swap()
                
                timestamp = backup_data.get('timestamp', 'desconocido')
                logger.info(f"🔄 Índice recargado exitosamente (timestamp: {timestamp})")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error recargando índice: {e}")
            return False
    
    def search(self, query: str, threshold: float = 0.3) -> List[Tuple[int, float]]:
        """Búsqueda semántica usando el índice activo"""
        try:
            with self.search_lock:
                if not self.active_index or self.active_index.ntotal == 0:
                    logger.warning("⚠️ Índice vacío o no disponible")
                    return []
                
                query_vec = self.model.encode([query], normalize_embeddings=True)
                total_productos = self.active_index.ntotal
                
                D, I = self.active_index.search(np.array(query_vec, dtype=np.float32), total_productos)
                
                resultados = []
                for score, faiss_idx in zip(D[0], I[0]):
                    if faiss_idx in self.active_faiss_idx_to_id and score >= threshold:
                        producto_id = self.active_faiss_idx_to_id[faiss_idx]
                        resultados.append((producto_id, float(score)))
                
                resultados.sort(key=lambda x: x[1], reverse=True)
                return resultados
                
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            return []
    
    def hybrid_search(self, query: str, threshold: float = 0.3) -> List[Tuple[int, float]]:
        resultados = self.search(query, threshold)
        query_lower = query.lower()
        
        with self.search_lock:
            for producto_id, producto in self.active_productos.items():
                match_exacto = False
                score_exacto = 1.0
                
                descripcion = producto.get('descripcion', '') or ''
                variante_comb = producto.get('variante_comb', '') or ''
                
                if (query_lower in descripcion.lower() or
                    query_lower in variante_comb.lower()):
                    match_exacto = True
                
                campos_busqueda = [descripcion, variante_comb]
                
                for campo in campos_busqueda:
                    if re.search(re.escape(query_lower), campo.lower()):
                        match_exacto = True
                        break
                
                if match_exacto:
                    if not any(result[0] == producto_id for result in resultados):
                        resultados.insert(0, (producto_id, score_exacto))
            
            resultados.sort(key=lambda x: x[1], reverse=True)
            return resultados
    
    def get_product_by_id(self, producto_id: int) -> Optional[Dict]:
        with self.search_lock:
            return self.active_productos.get(producto_id)
    
    def get_stats(self) -> Dict:
        with self.search_lock:
            return {
                "total_productos": len(self.active_productos),
                "faiss_total": self.active_index.ntotal if self.active_index else 0,
                "dimension": self.dimension,
                "index_loaded": self.active_index is not None,
                "service": "faiss_search"
            }

#Instancia global del servicio
search_service = SearchService()
 
#Endpoints
@app.get("/search")
def search_products(query: str = Query(..., description="Texto a buscar"), threshold: float = 0.45):
    try:
        resultados = search_service.hybrid_search(query, threshold)
        
        data = []
        for producto_id, score in resultados:
            producto = search_service.get_product_by_id(producto_id)
            
            if producto:
                data.append({
                    "id": producto["id"],
                    "nombre": producto["nombre"],
                    "descripcion": producto["descripcion"],
                    "variantes_comb": producto["variante_comb"],
                    "similitud": round(score, 3)
                })
        
        return JSONResponse(content={"query": query, "resultados": data})
    except Exception as e:
        logger.error(f"❌ Error en búsqueda: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/search/semantic")
def semantic_search(query: str = Query(..., description="Texto a buscar"), threshold: float = 0.3):
    try:
        resultados = search_service.search(query, threshold)
        
        data = []
        for producto_id, score in resultados:
            producto = search_service.get_product_by_id(producto_id)
            
            if producto:
                data.append({
                    "id": producto["id"],
                    "nombre": producto["nombre"],
                    "descripcion": producto["descripcion"],
                    "variantes_comb": producto["variante_comb"],
                    "similitud": round(score, 3)
                })
        
        return JSONResponse(content={"query": query, "resultados": data})
    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/reload_index")
def reload_index_endpoint(background_tasks: BackgroundTasks):
    try:
        # Ejecutar recarga en background para no bloquear el endpoint
        background_tasks.add_task(search_service.reload_index_from_files)
        return JSONResponse(content={"mensaje": "Recarga de índice iniciada en background"})
    except Exception as e:
        logger.error(f"❌ Error iniciando recarga: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/product/{producto_id}")
def get_product(producto_id: int):
    try:
        producto = search_service.get_product_by_id(producto_id)
        if producto:
            return JSONResponse(content=producto)
        else:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    try:
        stats = search_service.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    try:
        stats = search_service.get_stats()
        return {
            "status": "healthy",
            "service": "faiss_search",
            "index_loaded": stats["index_loaded"],
            "total_products": stats["total_productos"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "faiss_search",
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 FAISS Search Service iniciado")
    stats = search_service.get_stats()
    logger.info(f"📊 Productos cargados: {stats['total_productos']}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 FAISS Search Service detenido")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)