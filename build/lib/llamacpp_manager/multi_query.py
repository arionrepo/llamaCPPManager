# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/multi_query.py
# Description: Parallel querying of multiple LLM models for comparison
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-11

"""
Multi-Model Query Engine

Business Purpose: Enable querying multiple LLM models simultaneously to compare
responses, identify best answers, and make informed model selection decisions.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .chat_storage import ChatStorage


@dataclass
class ModelResponse:
    """
    Response from a single model.

    Business Purpose: Container for model response with performance metrics
    for easy comparison and analysis.
    """
    model_name: str
    content: str
    response_time_ms: int
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MultiModelQuery:
    """
    Query multiple models in parallel and compare responses.

    Business Purpose: Provide simultaneous access to multiple LLMs for
    comparing reasoning approaches, response quality, and speed.

    Example:
        query = MultiModelQuery()
        results = await query.ask(
            question="Explain quantum computing",
            models=["phi3", "qwen-coder-7b", "hermes-3"],
            save_to_history=True
        )
        for result in results:
            print(f"{result.model_name}: {result.content}")
    """

    def __init__(self, storage: Optional[ChatStorage] = None):
        """
        Initialize multi-model query engine.

        Args:
            storage: Optional ChatStorage instance for saving history

        Example:
            # Use default storage
            query = MultiModelQuery()

            # Or provide custom storage
            custom_storage = ChatStorage(Path("/tmp/chat.db"))
            query = MultiModelQuery(storage=custom_storage)
        """
        self.storage = storage or ChatStorage()

    async def ask(
        self,
        question: str,
        models: List[str],
        save_to_history: bool = True,
        conversation_id: Optional[int] = None,
        conversation_title: Optional[str] = None,
        timeout: int = 30
    ) -> List[ModelResponse]:
        """
        Ask the same question to multiple models in parallel.

        Business Purpose: Get multiple perspectives on the same question
        simultaneously, saving time and enabling direct comparison.

        Args:
            question: Question to ask all models
            models: List of model names to query
            save_to_history: Whether to save to database
            conversation_id: Optional existing conversation ID
            conversation_title: Title for new conversation (if saving)
            timeout: Max seconds to wait per model

        Returns:
            List of ModelResponse objects with results from each model

        Example:
            results = await query.ask(
                "Write a Python function to parse JSON",
                models=["phi3", "qwen-coder-7b", "hermes-3"],
                conversation_title="Code Generation Test"
            )

            # Results sorted by response time (fastest first)
            for result in results:
                if result.error:
                    print(f"{result.model_name}: ERROR - {result.error}")
                else:
                    print(f"{result.model_name} ({result.response_time_ms}ms):")
                    print(result.content[:200])
        """
        # Create conversation if saving and no conversation_id provided
        message_id = None
        if save_to_history:
            if conversation_id is None:
                title = conversation_title or f"Query: {question[:50]}"
                conversation_id = self.storage.create_conversation(title)

            message_id = self.storage.add_message(conversation_id, question)

        # Query all models in parallel
        tasks = [
            self._query_single_model(model_name, question, timeout)
            for model_name in models
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        results = []
        for model_name, response in zip(models, responses):
            if isinstance(response, Exception):
                results.append(ModelResponse(
                    model_name=model_name,
                    content="",
                    response_time_ms=0,
                    error=str(response)
                ))
            else:
                results.append(response)

        # Save responses to history
        if save_to_history and message_id:
            for result in results:
                if not result.error:
                    self.storage.add_response(
                        message_id,
                        result.model_name,
                        result.content,
                        result.response_time_ms,
                        result.tokens_used,
                        result.metadata
                    )

        # Sort by response time (fastest first)
        results.sort(key=lambda r: r.response_time_ms if not r.error else float('inf'))

        return results

    async def _query_single_model(
        self,
        model_name: str,
        question: str,
        timeout: int
    ) -> ModelResponse:
        """
        Query a single model (internal method).

        Business Purpose: Execute query with timing and error handling.

        Args:
            model_name: Name of model to query
            question: Question text
            timeout: Timeout in seconds

        Returns:
            ModelResponse with result or error
        """
        start_time = time.time()

        try:
            # Use subprocess to call CLI (works with existing infrastructure)
            process = await asyncio.create_subprocess_exec(
                "llamacpp-manager",
                "query",
                "chat",
                model_name,
                "--message",
                f"user:{question}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Model {model_name} timed out after {timeout}s")

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Check for errors
            if process.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                raise RuntimeError(f"Query failed: {error_msg}")

            # Parse response
            content = stdout.decode().strip()

            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            tokens_used = len(content) // 4

            return ModelResponse(
                model_name=model_name,
                content=content,
                response_time_ms=response_time_ms,
                tokens_used=tokens_used,
                metadata={"timeout": timeout}
            )

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ModelResponse(
                model_name=model_name,
                content="",
                response_time_ms=response_time_ms,
                error=str(e)
            )


def compare_models_sync(
    question: str,
    models: List[str],
    save_to_history: bool = True,
    conversation_title: Optional[str] = None,
    timeout: int = 30
) -> List[ModelResponse]:
    """
    Synchronous wrapper for asking multiple models (for CLI use).

    Business Purpose: Provide simple synchronous API for command-line
    tools that don't use async/await.

    Args:
        question: Question to ask
        models: List of model names
        save_to_history: Whether to save to database
        conversation_title: Title for new conversation
        timeout: Timeout per model in seconds

    Returns:
        List of ModelResponse objects

    Example:
        results = compare_models_sync(
            "Explain recursion",
            ["phi3", "qwen-coder-7b"],
            conversation_title="Programming Concepts"
        )
    """
    query = MultiModelQuery()

    # Run async code in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            query.ask(
                question,
                models,
                save_to_history,
                conversation_title=conversation_title,
                timeout=timeout
            )
        )
        return results
    finally:
        loop.close()
