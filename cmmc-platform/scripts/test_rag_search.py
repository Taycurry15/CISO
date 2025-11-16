#!/usr/bin/env python3
"""
CMMC Platform - RAG Search Test Script
Test semantic search over ingested documentation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from dotenv import load_dotenv
import os

from api.services import create_embedding_service, RAGService

load_dotenv()


async def test_search(query: str, top_k: int = 5):
    """Test RAG search with a query"""

    print("=" * 70)
    print("CMMC RAG Semantic Search Test")
    print("=" * 70)
    print(f"\nQuery: \"{query}\"")
    print(f"Top K: {top_k}\n")

    # Connect to database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/cmmc_platform")
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    # Initialize services
    embedding_service = create_embedding_service(
        provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("AI_API_KEY"),
        model_name=os.getenv("EMBEDDING_MODEL")
    )

    rag_service = RAGService(embedding_service, db_pool)

    # Perform search
    print("Searching...")
    results = await rag_service.retrieve_relevant_context(
        query=query,
        top_k=top_k,
        similarity_threshold=0.5
    )

    print(f"\nFound {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['document_title']}")
        print(f"   Control: {result.get('control_id', 'N/A')}")
        print(f"   Method: {result.get('method', 'N/A')}")
        print(f"   Similarity: {result['similarity_score']:.3f}")
        print(f"   Excerpt: {result['chunk_text'][:200]}...")
        print()

    await db_pool.close()


async def interactive_mode():
    """Interactive search mode"""
    print("=" * 70)
    print("CMMC RAG Interactive Search")
    print("=" * 70)
    print("\nEnter queries to search (or 'quit' to exit)")
    print("Examples:")
    print("  - multi-factor authentication")
    print("  - access control policy")
    print("  - incident response procedures")
    print("  - cryptographic protection\n")

    # Initialize services once
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/cmmc_platform")
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    embedding_service = create_embedding_service(
        provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("AI_API_KEY"),
        model_name=os.getenv("EMBEDDING_MODEL")
    )

    rag_service = RAGService(embedding_service, db_pool)

    while True:
        try:
            query = input("\nQuery> ").strip()

            if query.lower() in ['quit', 'exit', 'q']:
                break

            if not query:
                continue

            results = await rag_service.retrieve_relevant_context(
                query=query,
                top_k=5,
                similarity_threshold=0.5
            )

            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. [{result['similarity_score']:.3f}] {result['document_title']}")
                print(f"   {result['chunk_text'][:150]}...")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    await db_pool.close()
    print("\nGoodbye!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test CMMC RAG semantic search")
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--top-k', '-k', type=int, default=5, help='Number of results (default: 5)')

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mode())
    elif args.query:
        query = ' '.join(args.query)
        asyncio.run(test_search(query, args.top_k))
    else:
        # Default test queries
        test_queries = [
            "multi-factor authentication requirements",
            "access control for CUI",
            "incident response and reporting",
            "audit logging requirements"
        ]

        async def run_tests():
            for query in test_queries:
                await test_search(query, top_k=3)
                print("\n" + "-" * 70 + "\n")

        asyncio.run(run_tests())
