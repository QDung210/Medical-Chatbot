from pathlib import Path
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from typing import List, Dict
from .model_setup import load_model
from .utils import get_hardware, logger, COLLECTION, resources, DEFAULT_MODEL
from .database.postgres_memory import get_by_session_id

# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent / ".cache"
EMBEDDINGS_MODEL = CACHE_DIR / "model"

prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=(
        "Bạn là một trợ lý AI chuyên ngành y tế. Trả lời câu hỏi sau bằng tiếng Việt một cách đầy đủ và chi tiết.\n"
        "Nếu được thì hãy đưa ra nguyên nhân, triệu chứng, cách điều trị và các thông tin liên quan khác.\n"
        "Nếu không phải câu hỏi về y tế, hãy nói rằng bạn không thể giúp.\n"
        "Sau khi trả lời xong, hãy khuyên người hỏi nên tham khảo ý kiến bác sĩ.\n\n"
        "Lịch sử cuộc trò chuyện:\n{chat_history}\n\n"
        "Ngữ cảnh từ tài liệu y tế:\n{context}\n\n"
        "Câu hỏi: {question}\n\n"
        "Trả lời:"
    )
)

# Retriever from Qdrant
def retrieve_context(question: str, top_k=3) -> dict:
    vec = resources.embedder.encode(question).tolist()
    results = resources.client.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=top_k,
        with_payload=True
    )
    contexts = []
    sources = []
    seen_titles = set()
    for i, pt in enumerate(results.points):
        logger.info(f"Point {i+1}: score={pt.score}, payload keys={list(pt.payload.keys()) if pt.payload else 'None'}")
        title = pt.payload.get('metadata', {}).get('title', '') if pt.payload else ''
        if title in seen_titles:
            continue
        seen_titles.add(title)
        url = pt.payload.get('metadata', {}).get('url', '') if pt.payload else ''
        content = pt.payload.get('page_content', '') if pt.payload else ''
        
        if content:
            contexts.append(content)
            sources.append({
                'title': title,
                'url': url,
                'score': pt.score
            })
    return {
        'context': "\n---\n".join(contexts),
        'sources': sources
    }

def create_rag_chain_with_memory(model):
    def rag_logic(inputs):
        question = inputs["question"]
        chat_history = inputs.get("chat_history", [])
        
        # Format chat history for context 
        history_text = ""
        if chat_history:
            recent_history = chat_history[-2:]  
            history_lines = []
            
            for msg in recent_history:
                if hasattr(msg, 'content'):
                    content = msg.content
                    # Cắt ngắn nếu câu trả lời quá dài
                    if len(content) > 150:
                        content = content[:150] + "..."
                    
                    if msg.__class__.__name__ == 'HumanMessage':
                        history_lines.append(f"Người dùng: {content}")
                    elif msg.__class__.__name__ == 'AIMessage':
                        history_lines.append(f"AI: {content}")
            
            history_text = "\n".join(history_lines)
        
        if not history_text:
            history_text = "Chưa có lịch sử cuộc trò chuyện."
        retrieval_result = retrieve_context(question)
        context = retrieval_result['context']
        formatted_prompt = prompt.format(
            context=context, 
            question=question, 
            chat_history=history_text
        )
        response = model.invoke(formatted_prompt)
        return response.content
    
    # Create proper Runnable from function
    rag_runnable = RunnableLambda(rag_logic)
    
    # Create chain with memory
    chain_with_memory = RunnableWithMessageHistory(
        rag_runnable,
        get_by_session_id,
        input_messages_key="question",
        history_messages_key="chat_history",
    )
    
    return chain_with_memory

def generate_answer_stream(question: str, model, session_id: str = "default"):
    """Generate streaming answer with memory"""
    chain = create_rag_chain_with_memory(model)
    
    result = chain.invoke(
        {"question": question},
        config={"configurable": {"session_id": session_id}}
    )
    
    retrieval_result = retrieve_context(question)
    sources = retrieval_result['sources']
    
    answer = result if isinstance(result, str) else str(result)
    for char in answer:
        yield {
            'content': char,
            'sources': sources,
            'type': 'content'
        }
    yield {
        'content': '',
        'sources': sources,
        'type': 'sources'
    }



