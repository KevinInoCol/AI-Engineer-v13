import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Cargar variables de entorno
load_dotenv()


def crear_agente_basico():
    """
    Crea un agente básico que consulta la base de datos vectorial
    """
    # Configuración de Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    client = create_client(supabase_url, supabase_key)
    
    # Modelo de embeddings (el mismo que usaste para cargar)
    embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')
    
    # Conectar al vectorstore existente
    vectorstore = SupabaseVectorStore(
        client=client,
        embedding=embedding_model,
        table_name="documents_langchain_asistente_de_ventas",
        query_name="match_documents_langchain_asistente_de_ventas"
    )
    
    # Crear retriever
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3}  # Recupera los 3 documentos más relevantes
    )
    
    # Modelo de lenguaje
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.7
    )
    
    # Prompt personalizado
    prompt_template = """Eres un asistente de ventas experto sobre DATAPATH. 
Usa la siguiente información para responder la pregunta del usuario de manera clara y precisa.

Contexto:
{context}

Pregunta: {question}

Respuesta detallada:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template, 
        input_variables=["context", "question"]
    )
    
    # Crear la cadena de RetrievalQA
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    return qa_chain


def mostrar_bienvenida():
    """
    Muestra el mensaje de bienvenida
    """
    print("\n" + "="*60)
    print("🤖 AGENTE DE CONSULTA - DATAPATH")
    print("="*60)
    print("Bienvenido! Puedo responder preguntas sobre DATAPATH.")
    print("Escribe 'salir' o 'exit' para terminar.")
    print("="*60 + "\n")


def ejecutar_interfaz():
    """
    Interfaz de terminal para consultar el agente
    """
    mostrar_bienvenida()
    
    # Crear el agente
    print("⏳ Cargando agente y conectando a la base de datos...")
    agente = crear_agente_basico()
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
            
            # Realizar la consulta
            print("\n🔍 Consultando base de conocimientos...")
            resultado = agente.invoke({"query": pregunta})
            
            # Mostrar respuesta
            print("\n" + "-"*60)
            print("🤖 Respuesta:")
            print("-"*60)
            print(resultado['result'])
            print("-"*60)
            
            # Mostrar fuentes (opcional)
            if resultado.get('source_documents'):
                print(f"\n📚 Basado en {len(resultado['source_documents'])} documentos de la base de conocimientos.")
            
            print("\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            continue


if __name__ == '__main__':
    ejecutar_interfaz()
