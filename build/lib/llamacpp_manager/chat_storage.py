# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/chat_storage.py
# Description: SQLite database storage for multi-model chat comparisons and history
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-11

"""
Chat Storage Module

Business Purpose: Store all multi-model chat interactions in a local database
to build a searchable knowledge base and enable model performance analysis.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class ChatStorage:
    """
    Local SQLite database for storing chat conversations and model responses.

    Business Purpose: Provides persistent storage for all LLM interactions,
    enabling users to search history, compare model performance, and build
    a personal knowledge base of AI responses.

    Example:
        storage = ChatStorage()
        conversation_id = storage.create_conversation("Quantum Computing Q&A")
        message_id = storage.add_message(conversation_id, "Explain quantum computing")
        storage.add_response(message_id, "phi3", "Quantum computing uses...", 2100)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize chat storage with SQLite database.

        Args:
            db_path: Path to database file (defaults to app support directory)

        Example:
            # Use default location
            storage = ChatStorage()

            # Or specify custom location
            storage = ChatStorage(Path("/tmp/test_chat.db"))
        """
        if db_path is None:
            # Default: ~/Library/Application Support/llamaCPPManager/chat_history.db
            app_support = Path.home() / "Library" / "Application Support" / "llamaCPPManager"
            app_support.mkdir(parents=True, exist_ok=True)
            db_path = app_support / "chat_history.db"

        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """
        Initialize database schema if it doesn't exist.

        Business Purpose: Create tables for conversations, messages, and responses
        with proper indexes for fast searching.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                notes TEXT
            )
        """)

        # Messages table (questions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # Responses table (model answers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                content TEXT NOT NULL,
                response_time_ms INTEGER,
                tokens_used INTEGER,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
        """)

        # Indexes for fast searching
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_message ON responses(message_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_model ON responses(model_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

        # Full-text search virtual tables
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(content, content=messages, content_rowid=id)
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS responses_fts
            USING fts5(content, model_name, content=responses, content_rowid=id)
        """)

        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS responses_fts_insert AFTER INSERT ON responses BEGIN
                INSERT INTO responses_fts(rowid, content, model_name)
                VALUES (new.id, new.content, new.model_name);
            END
        """)

        conn.commit()
        conn.close()

    def create_conversation(self, title: str, tags: Optional[List[str]] = None) -> int:
        """
        Create a new conversation.

        Business Purpose: Start a new chat session that can contain multiple
        questions and responses for organized knowledge management.

        Args:
            title: Conversation title (e.g., "Quantum Computing Q&A")
            tags: Optional list of tags (e.g., ["research", "physics"])

        Returns:
            Conversation ID

        Example:
            conversation_id = storage.create_conversation(
                "Python Best Practices",
                tags=["coding", "python"]
            )
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        tags_json = json.dumps(tags) if tags else None

        cursor.execute(
            "INSERT INTO conversations (title, tags) VALUES (?, ?)",
            (title, tags_json)
        )

        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return conversation_id

    def add_message(self, conversation_id: int, content: str) -> int:
        """
        Add a question/message to a conversation.

        Business Purpose: Record user questions for later retrieval and analysis.

        Args:
            conversation_id: ID of parent conversation
            content: Question text

        Returns:
            Message ID

        Example:
            message_id = storage.add_message(
                conversation_id,
                "How does quantum entanglement work?"
            )
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages (conversation_id, content) VALUES (?, ?)",
            (conversation_id, content)
        )

        message_id = cursor.lastrowid

        # Update conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )

        conn.commit()
        conn.close()

        return message_id

    def add_response(
        self,
        message_id: int,
        model_name: str,
        content: str,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a model response to a message.

        Business Purpose: Store LLM responses with performance metrics for
        comparison and analysis.

        Args:
            message_id: ID of the question being answered
            model_name: Name of model (e.g., "phi3", "qwen-coder-7b")
            content: Response text
            response_time_ms: Time taken to respond in milliseconds
            tokens_used: Number of tokens in response
            metadata: Additional info (temperature, max_tokens, etc.)

        Returns:
            Response ID

        Example:
            response_id = storage.add_response(
                message_id,
                "phi3",
                "Quantum entanglement is when two particles...",
                response_time_ms=2100,
                tokens_used=150
            )
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            """INSERT INTO responses
               (message_id, model_name, content, response_time_ms, tokens_used, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, model_name, content, response_time_ms, tokens_used, metadata_json)
        )

        response_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return response_id

    def rate_response(self, response_id: int, rating: int) -> None:
        """
        Rate a model response (1-5 stars).

        Business Purpose: Track response quality to identify best-performing
        models for specific use cases.

        Args:
            response_id: ID of response to rate
            rating: Rating from 1 (poor) to 5 (excellent)

        Example:
            storage.rate_response(response_id, 5)  # Excellent response
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE responses SET rating = ? WHERE id = ?",
            (rating, response_id)
        )

        conn.commit()
        conn.close()

    def search_messages(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across all messages (questions).

        Business Purpose: Find past questions quickly to avoid re-asking
        or to reference previous discussions.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching messages with conversation info

        Example:
            results = storage.search_messages("quantum entanglement")
            for msg in results:
                print(f"{msg['content']} (from: {msg['conversation_title']})")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                m.id, m.content, m.created_at,
                c.id as conversation_id, c.title as conversation_title
            FROM messages_fts fts
            JOIN messages m ON fts.rowid = m.id
            JOIN conversations c ON m.conversation_id = c.id
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get full conversation with all messages and responses.

        Business Purpose: Retrieve complete conversation history for review
        and continued discussion.

        Args:
            conversation_id: ID of conversation to retrieve

        Returns:
            Dictionary with conversation metadata, messages, and responses

        Example:
            conv = storage.get_conversation(123)
            print(f"Title: {conv['title']}")
            for msg in conv['messages']:
                print(f"Q: {msg['content']}")
                for resp in msg['responses']:
                    print(f"  {resp['model_name']}: {resp['content']}")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get conversation metadata
        cursor.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )

        conv_row = cursor.fetchone()
        if not conv_row:
            conn.close()
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = dict(conv_row)
        if conversation['tags']:
            conversation['tags'] = json.loads(conversation['tags'])

        # Get all messages
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,)
        )

        messages = []
        for msg_row in cursor.fetchall():
            message = dict(msg_row)

            # Get responses for this message
            cursor.execute(
                "SELECT * FROM responses WHERE message_id = ? ORDER BY created_at",
                (message['id'],)
            )

            responses = []
            for resp_row in cursor.fetchall():
                response = dict(resp_row)
                if response['metadata']:
                    response['metadata'] = json.loads(response['metadata'])
                responses.append(response)

            message['responses'] = responses
            messages.append(message)

        conversation['messages'] = messages
        conn.close()

        return conversation

    def get_model_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for models.

        Business Purpose: Analyze which models perform best for making
        informed model selection decisions.

        Args:
            model_name: Optional specific model (if None, returns all models)

        Returns:
            Statistics including query count, avg response time, avg rating

        Example:
            stats = storage.get_model_stats("phi3")
            print(f"Average rating: {stats['avg_rating']} stars")
            print(f"Average response time: {stats['avg_response_time_ms']}ms")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if model_name:
            cursor.execute("""
                SELECT
                    model_name,
                    COUNT(*) as total_responses,
                    AVG(response_time_ms) as avg_response_time_ms,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as rated_responses
                FROM responses
                WHERE model_name = ?
                GROUP BY model_name
            """, (model_name,))

            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else {}
        else:
            cursor.execute("""
                SELECT
                    model_name,
                    COUNT(*) as total_responses,
                    AVG(response_time_ms) as avg_response_time_ms,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as rated_responses
                FROM responses
                GROUP BY model_name
                ORDER BY total_responses DESC
            """)

            results = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return {"models": results}

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent conversations.

        Business Purpose: Browse conversation history to find and continue
        past discussions.

        Args:
            limit: Maximum number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversations with message counts

        Example:
            conversations = storage.list_conversations(limit=10)
            for conv in conversations:
                print(f"{conv['title']} ({conv['message_count']} messages)")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.*,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        results = [dict(row) for row in cursor.fetchall()]

        for conv in results:
            if conv['tags']:
                conv['tags'] = json.loads(conv['tags'])

        conn.close()
        return results
