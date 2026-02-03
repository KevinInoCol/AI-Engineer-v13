import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from supabase import create_client
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain import hub

# Cargar variables de entorno
load_dotenv()


def crear_herramienta_busqueda():
    """
    Crea una herramienta para buscar en la base de datos vectorial
    haciendo la búsqueda de similitud completamente en Python
    """
    import numpy as np
    
    # Configuración de Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    client = create_client(supabase_url, supabase_key)
    
    # Modelo de embeddings
    embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')
    
    def calcular_similitud_coseno(vec1, vec2):
        """Calcula la similitud de coseno entre dos vectores"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return 1 - np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def buscar_en_base_conocimiento(query: str) -> str:
        """
        Busca información en la base de conocimientos de DATAPATH
        """
        try:
            # 1. Convertir la consulta en embedding
            print("🔍 Generando embedding de la query...")
            query_embedding = embedding_model.embed_query(query)
            
            # 2. Obtener TODOS los documentos de la tabla
            print("📥 Obteniendo documentos de Supabase...")
            result = client.table('documents_langchain_asistente_de_ventas').select('*').execute()
            
            if not result.data:
                return "No hay documentos en la base de conocimientos."
            
            print(f"📚 Total de documentos en BD: {len(result.data)}")
            
            # 3. Calcular similitud para cada documento
            documentos_con_score = []
            for doc in result.data:
                if doc.get('embedding'):
                    # Convertir el embedding de Supabase (puede venir como string o lista)
                    doc_embedding = doc['embedding']
                    if isinstance(doc_embedding, str):
                        # Si es string, parsearlo como array de floats
                        import json
                        doc_embedding = json.loads(doc_embedding)
                    
                    # Convertir a array de floats
                    doc_embedding = [float(x) for x in doc_embedding]
                    
                    score = calcular_similitud_coseno(query_embedding, doc_embedding)
                    documentos_con_score.append({
                        'content': doc.get('content', ''),
                        'metadata': doc.get('metadata', {}),
                        'score': score
                    })
            
            # 4. Ordenar por similitud (menor score = más similar)
            documentos_con_score.sort(key=lambda x: x['score'])
            
            # 5. Tomar los top 5
            top_docs = documentos_con_score[:5]
            
            if not top_docs:
                return "No encontré información relevante en la base de conocimientos."
            
            # 6. Formatear los resultados
            resultado = "Información encontrada en la base de conocimientos:\n\n"
            for i, doc in enumerate(top_docs, 1):
                content = doc['content']
                score = doc['score']
                resultado += f"Fragmento {i} (similitud: {1-score:.3f}):\n{content}\n\n"
            
            print(f"✅ Documentos recuperados: {len(top_docs)}")
            return resultado
            
        except Exception as e:
            print(f"❌ Error al buscar: {e}")
            import traceback
            traceback.print_exc()
            return f"Error al buscar: {str(e)}"
    
    return buscar_en_base_conocimiento


def crear_agente_react():
    """
    Crea un agente ReAct simple
    """
    # Crear la herramienta de búsqueda
    buscar_func = crear_herramienta_busqueda()
    
    tool = Tool(
        name="BuscarDatapath",
        func=buscar_func,
        description="Útil para buscar información sobre DATAPATH. Usa esta herramienta cuando necesites responder preguntas sobre DATAPATH, sus programas, docentes, o cualquier información relacionada."
    )
    
    tools = [tool]
    
    # Modelo de lenguaje
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.7
    )
    
    # Prompt para ReAct (usar el prompt base de LangChain)
    prompt = hub.pull("hwchase17/react")
    
    # Crear el agente ReAct
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    # Crear el ejecutor del agente
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # Para ver el razonamiento del agente
        handle_parsing_errors=True,
        max_iterations=3
    )
    
    return agent_executor


def mostrar_bienvenida():
    """
    Muestra el mensaje de bienvenida
    """
    print("\n" + "="*60)
    print("🤖 AGENTE ReAct - DATAPATH")
    print("="*60)
    print("Agente con capacidad de razonamiento y acción.")
    print("Escribe 'salir' o 'exit' para terminar.")
    print("="*60 + "\n")


def ejecutar_interfaz():
    """
    Interfaz de terminal para consultar el agente
    """
    mostrar_bienvenida()
    
    # Crear el agente
    print("⏳ Cargando agente ReAct...")
    agente = crear_agente_react()
    print("✅ Agente listo!\n")
    
    # Loop de conversación
    while True:
        try:
            # Obtener pregunta del usuario
            pregunta = input("👤 Tu pregunta: ").strip()
            
            # Verificar si quiere salir
            if pregunta.lower() in ['salir', 'exit', 'quit', 'q']:
                print("\n👋 ¡Hasta luego!\n")
                break
            
            # Verificar que no esté vacía
            if not pregunta:
                print("⚠️  Por favor, escribe una pregunta.\n")
                continue
            
            print("\n" + "="*60)
            # Ejecutar el agente
            resultado = agente.invoke({"input": pregunta})
            
            # Mostrar respuesta final
            print("="*60)
            print("🤖 Respuesta Final:")
            print("-"*60)
            print(resultado['output'])
            print("="*60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            continue


if __name__ == '__main__':
    ejecutar_interfaz()
