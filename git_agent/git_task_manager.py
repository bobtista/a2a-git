import asyncio
import logging
import traceback
from collections.abc import AsyncIterable

from common.server.task_manager import InMemoryTaskManager
from common.types import (
    Artifact,
    InternalError,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

logger = logging.getLogger(__name__)


class GitTaskManager(InMemoryTaskManager):
    """Task manager for Git MCP agent."""

    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        validation_error = self._validate_request(request)
        if validation_error:
            return SendTaskResponse(id=request.id, error=validation_error.error)

        await self.upsert_task(request.params)
        await self.update_store(
            request.params.id, TaskStatus(state=TaskState.WORKING), None
        )

        task_send_params: TaskSendParams = request.params
        query = self._extract_user_query(task_send_params)

        try:
            agent_response = await self.agent.git_command(query)
            return await self._handle_send_task(request, agent_response)
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            return SendTaskResponse(
                id=request.id,
                error=InternalError(message=f"Error during on_send_task: {e!s}"),
            )

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        try:
            error = self._validate_request(request)
            if error:
                return error

            await self.upsert_task(request.params)
            task_send_params: TaskSendParams = request.params
            sse_event_queue = await self.setup_sse_consumer(task_send_params.id, False)

            asyncio.create_task(self._handle_send_task_streaming(request))

            return self.dequeue_events_for_sse(
                request.id, task_send_params.id, sse_event_queue
            )
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            print(traceback.format_exc())
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while streaming the response"
                ),
            )

    async def _handle_send_task(
        self, request: SendTaskRequest, agent_response: str
    ) -> SendTaskResponse:
        task_send_params: TaskSendParams = request.params
        task_id = task_send_params.id
        history_length = task_send_params.historyLength
        task_status = TaskStatus(state=TaskState.COMPLETED)
        parts = [TextPart(type="text", text=agent_response)]
        artifact = Artifact(parts=parts)
        updated_task = await self.update_store(task_id, task_status, [artifact])
        task_result = self.append_task_history(updated_task, history_length)
        return SendTaskResponse(id=request.id, result=task_result)

    async def _handle_send_task_streaming(self, request: SendTaskStreamingRequest):
        task_send_params: TaskSendParams = request.params
        query = self._extract_user_query(task_send_params)
        try:
            # TODO: Implement streaming logic with your agent if supported
            # For now, just call the agent synchronously and send as one chunk
            agent_response = await self.agent.git_command(query)
            parts = [TextPart(type="text", text=agent_response)]
            artifact = Artifact(parts=parts, index=0, append=False)
            task_status = TaskStatus(state=TaskState.COMPLETED)
            await self.update_store(task_send_params.id, task_status, [artifact])
            task_artifact_update_event = TaskArtifactUpdateEvent(
                id=task_send_params.id, artifact=artifact
            )
            await self.enqueue_events_for_sse(
                task_send_params.id, task_artifact_update_event
            )
            task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id, status=task_status, final=True
            )
            await self.enqueue_events_for_sse(task_send_params.id, task_update_event)
        except Exception as e:
            logger.error(f"An error occurred while streaming the response: {e}")
            logger.error(traceback.format_exc())
            await self.enqueue_events_for_sse(
                task_send_params.id,
                InternalError(
                    message=f"An error occurred while streaming the response: {e}"
                ),
            )

    def _validate_request(
        self, request: SendTaskRequest | SendTaskStreamingRequest
    ) -> JSONRPCResponse | None:
        # TODO: Add modality validation if needed
        return None

    def _extract_user_query(self, task_send_params: TaskSendParams) -> str:
        part = task_send_params.message.parts[0]
        if not isinstance(part, TextPart):
            raise ValueError("Only text parts are supported")
        return part.text
