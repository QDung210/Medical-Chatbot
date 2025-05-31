#!/usr/bin/env python3
"""
Test script for Qdrant Cloud connection
"""
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vector_store import connect_to_qdrant
from model_setup import load_embedding_model

def test_qdrant_cloud():
    print("=== QDRANT CLOUD CONNECTION TEST ===\n")
    
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print("⚠️ No .env file found. Using system environment variables.")
    
    # Check credentials
    qdrant_url = os.getenv('QDRANT_CLOUD_URL')
    qdrant_key = os.getenv('QDRANT_API_KEY')
    
    print("\n📋 Checking credentials:")
    print(f"- QDRANT_CLOUD_URL: {'✅ Set' if qdrant_url else '❌ Not set'}")
    print(f"- QDRANT_API_KEY: {'✅ Set' if qdrant_key else '❌ Not set'}")
    
    if not qdrant_url or not qdrant_key:
        print("\n❌ ERROR: Missing Qdrant Cloud credentials!")
        print("\nPlease create a .env file in the rag_pipeline directory with:")
        print("QDRANT_CLOUD_URL=https://your-cluster-url.qdrant.io")
        print("QDRANT_API_KEY=your-api-key-here")
        print("\nYou can get these from: https://cloud.qdrant.io/")
        return False
    
    # Test connection
    print("\n🔌 Testing connection to Qdrant Cloud...")
    client = connect_to_qdrant()
    
    if not client:
        print("❌ Failed to connect to Qdrant Cloud!")
        return False
    
    # List collections
    print("\n📦 Collections in your Qdrant Cloud:")
    try:
        collections = client.get_collections().collections
        if collections:
            for coll in collections:
                coll_info = client.get_collection(coll.name)
                print(f"  - {coll.name}: {coll_info.points_count} vectors")
        else:
            print("  (No collections found)")
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
    
    return True

def test_query():
    """Test a simple query"""
    print("\n=== TESTING QUERY FUNCTIONALITY ===\n")
    
    from rag_pipeline import create_rag_pipeline
    
    try:
        # Create pipeline
        print("📦 Creating RAG pipeline...")
        pipeline = create_rag_pipeline()
        
        # Test queries
        test_questions = [
            "căng cơ đùi là gì?",
            "triệu chứng của cúm A",
            "cách điều trị đau dạ dày"
        ]
        
        for question in test_questions:
            print(f"\n🔍 Query: {question}")
            result = pipeline.query(question)
            
            if result['context_used']:
                print(f"✅ Found {len(result['sources'])} relevant documents")
                print(f"📝 Answer preview: {result['answer'][:200]}...")
            else:
                print("⚠️ No relevant documents found")
                
    except Exception as e:
        print(f"\n❌ Error during query test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test connection first
    if test_qdrant_cloud():
        print("\n✅ Qdrant Cloud connection successful!")
        
        # Ask if user wants to test queries
        print("\n" + "="*50)
        response = input("\nDo you want to test some queries? (y/n): ")
        if response.lower() == 'y':
            test_query()
    else:
        print("\n❌ Please fix the connection issues above and try again.") 