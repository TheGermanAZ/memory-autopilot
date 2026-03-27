from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class CallerProfile(BaseModel):
    caller_id: str
    customer_name: str
    issue_summary: str
    issue_type: str
    order_id: str
    customer_sentiment: str
    open_actions: str
    first_seen_at: datetime
    updated_at: datetime


class DynamicVariablesResponse(BaseModel):
    dynamic_variables: dict[str, str]


class MemorySnapshot(BaseModel):
    conversation_id: str
    caller_id: str
    agent_id: str | None
    source: Literal["webhook", "demo"]
    data_collection: dict
    transcript_summary: str | None
    created_at: datetime


class DemoExtractionRequest(BaseModel):
    transcript: str


class DemoExtractionResponse(BaseModel):
    """Demo-only. Not used by the webhook path."""
    customer_name: str
    issue_summary: str
    issue_type: str
    order_id: str
    customer_sentiment: str
    open_actions: str


class PostCallWebhookPayload(BaseModel):
    """Shape of the ElevenLabs post-call transcription webhook."""
    agent_id: str
    conversation_id: str
    status: str | None = None
    transcript: list[dict] | None = None
    analysis: dict | None = None

    def get_data_collection_results(self) -> dict:
        if self.analysis and "data_collection_results" in self.analysis:
            return self.analysis["data_collection_results"]
        return {}

    def get_transcript_summary(self) -> str | None:
        if self.analysis:
            return self.analysis.get("transcript_summary")
        return None


class ConversationInitPayload(BaseModel):
    caller_id: str
    agent_id: str
    called_number: str | None = None
    call_sid: str | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str
