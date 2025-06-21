from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from .utils import logger, COLLECTION, resources, tracer
from .database.postgres_memory import get_by_session_id

prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=(
        "Bạn là một trợ lý AI chuyên ngành y tế. Trả lời câu hỏi sau bằng tiếng Việt một cách đầy đủ và chi tiết.\n"
        "Nếu được thì hãy đưa ra nguyên nhân, triệu chứng, cách điều trị và các thông tin liên quan khác.\n"
        "Nếu không phải câu hỏi về y tế, hãy nói rằng bạn không thể giúp.\n"
        "Sau khi trả lời xong, hãy khuyên người hỏi nên tham khảo ý kiến bác sĩ.\n\n"
        "QUAN TRỌNG: \n"
        "- Hãy chú ý đến lịch sử cuộc trò chuyện để hiểu ngữ cảnh.\n"
        "- Nếu câu hỏi hiện tại liên quan đến chủ đề đã thảo luận trước đó, hãy BỔ SUNG THÊM thông tin mới.\n"
        "- ĐỪNG lặp lại những gì đã trả lời trong lịch sử cuộc trò chuyện.\n"
        "- Chỉ cung cấp thông tin mới, bổ sung để hoàn thiện câu trả lời.\n"
        "- ĐỪNG giải thích bạn hiểu gì về câu hỏi. Chỉ trả lời trực tiếp.\n\n"
        "Lịch sử cuộc trò chuyện:\n{chat_history}\n\n"
        "Ngữ cảnh từ tài liệu y tế:\n{context}\n\n"
        "Câu hỏi: {question}\n\n"
        "Trả lời:"
    )
)

def retrieve_context(question: str, top_k=3) -> dict:
    with tracer.start_as_current_span("retrieve_context") as span:
        span.set_attribute("question.length", len(question))
        span.set_attribute("top_k", top_k)
        
        # Encode question to vector
        with tracer.start_as_current_span("encode_question"):
            vec = resources.embedder.encode(question).tolist()
        
        # Query vector database
        with tracer.start_as_current_span("query_qdrant") as query_span:
            results = resources.client.query_points(
                collection_name=COLLECTION,
                query=vec,
                limit=top_k,
                with_payload=True
            )
            query_span.set_attribute("results.count", len(results.points))
        
        # Process results
        contexts = []
        sources = []
        seen_titles = set()
        for i, pt in enumerate(results.points):
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
        
        span.set_attribute("contexts.count", len(contexts))
        span.set_attribute("sources.count", len(sources))
        
        return {
            'context': "\n---\n".join(contexts),
            'sources': sources
        }

def create_rag_chain_with_memory(model):
    def rag_logic(inputs):
        question = inputs["question"]
        chat_history = inputs.get("chat_history", [])
        
        logger.info(f"Original question: {question}")
        logger.info(f"Chat history length: {len(chat_history)}")
        
        # Format chat history for context 
        history_text = ""
        
        if chat_history:
            recent_history = chat_history[-4:]  
            history_lines = []
            
            for msg in recent_history:
                if hasattr(msg, 'content'):
                    content = msg.content
                    if len(content) > 300:
                        content = content[:300] + "..."
                    
                    if msg.__class__.__name__ == 'HumanMessage':
                        history_lines.append(f"Người dùng: {content}")
                    elif msg.__class__.__name__ == 'AIMessage':
                        history_lines.append(f"AI: {content}")
            
            history_text = "\n".join(history_lines)
            
            # Check for follow-up questions and modify the question
            followup_words = ['còn', 'nào', 'thêm', 'khác', 'nữa']
            has_followup = any(word in question.lower() for word in followup_words)
            
            logger.info(f"Has followup words: {has_followup}")
            
            if has_followup and len(recent_history) >= 2:
                # Get the last user question
                for msg in reversed(recent_history):
                    if msg.__class__.__name__ == 'HumanMessage':
                        last_question = msg.content
                        original_question = question
                        question = f"{last_question} {question}".strip()
                        logger.info(f"Follow-up detected!")
                        logger.info(f"  - Last question: {last_question}")
                        logger.info(f"  - Current question: {original_question}")
                        logger.info(f"  - Modified question: {question}")
                        break
        
        if not history_text:
            history_text = "Chưa có lịch sử cuộc trò chuyện."
        
        retrieval_result = retrieve_context(question)
        
        formatted_prompt = prompt.format(
            context=retrieval_result['context'], 
            question=question, 
            chat_history=history_text
        )
        response = model.invoke(formatted_prompt)
        
        global _last_sources
        _last_sources = retrieval_result['sources']
        
        return response.content

    rag_runnable = RunnableLambda(rag_logic)
    
    chain_with_memory = RunnableWithMessageHistory(
        rag_runnable,
        get_by_session_id,
        input_messages_key="question",
        history_messages_key="chat_history",
    )
    
    return chain_with_memory

# Global variable to store sources
_last_sources = []

def generate_answer_stream(question: str, model, session_id: str = "default"):
    """Generate streaming answer with memory"""
    
    with tracer.start_as_current_span("generate_answer_stream") as span:
        span.set_attribute("question.length", len(question))
        span.set_attribute("session_id", session_id)
        
        try:
            logger.info(f"Processing question: {question} for session: {session_id}")
            
            with tracer.start_as_current_span("create_rag_chain"):
                chain = create_rag_chain_with_memory(model)
            
            with tracer.start_as_current_span("invoke_chain") as invoke_span:
                result = chain.invoke(
                    {"question": question},
                    config={"configurable": {"session_id": session_id}}
                )
                invoke_span.set_attribute("result.length", len(result) if result else 0)
            
            logger.info(f"Generated response length: {len(result) if result else 0}")
            
            global _last_sources
            sources = _last_sources
            span.set_attribute("sources.count", len(sources))
            
            # Check if result is a string
            if isinstance(result, str):
                # Stream character by character for better UX
                for char in result:
                    yield {
                        'content': char,
                        'sources': sources,
                        'type': 'content'
                    }
            else:
                # If result is not string, convert to string first
                result_str = str(result)
                for char in result_str:
                    yield {
                        'content': char,
                        'sources': sources,
                        'type': 'content'
                    }
            
            # Send sources at the end
            yield {
                'content': '',
                'sources': sources,
                'type': 'sources'
            }
            
            logger.info("Successfully completed response generation")
            
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in generate_answer_stream: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return error message
            error_message = "❓ Chatbot không có đủ thông tin đáng tin cậy để trả lời câu hỏi này."
            for char in error_message:
                yield {
                    'content': char,
                    'sources': [],
                    'type': 'content'
                }
