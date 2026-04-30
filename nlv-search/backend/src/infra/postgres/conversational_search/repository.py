from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.infra.postgres.conversational_search.models import Chat, ChatMessage

_CHAT_TITLE_LEN = 40


def _build_chat_title(content: str, limit: int = _CHAT_TITLE_LEN) -> str | None:
    """Derive a chat title from the first user message, truncated to ``limit`` chars.

    Args:
        content: Raw message content.
        limit: Maximum title length before truncation.

    Returns:
        Normalized title string, or None if content is blank.
    """

    normalized = " ".join(content.split())

    if not normalized:
        return None

    if len(normalized) <= limit:
        return normalized

    return f"{normalized[:limit].rstrip()}..."


class ChatRepository:
    """PostgreSQL repository for chat and message CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an active SQLAlchemy async session."""

        self.session = session

    async def create_chat(self, user_id: str, title: str | None = None) -> Chat:
        """Create a new chat for the given user.

        Args:
            user_id: UUID of the owning user.
            title: Optional initial title; auto-generated from first message if omitted.

        Returns:
            Newly created Chat instance.
        """

        chat = Chat(user_id=user_id, title=title)
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)
        return chat

    async def get_chat(self, chat_id: str) -> Chat | None:
        """Fetch a chat by ID without loading messages.

        Args:
            chat_id: Chat UUID string.

        Returns:
            Chat instance or None.
        """

        result = await self.session.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalar_one_or_none()

    async def get_chat_with_messages(
        self, chat_id: str, user_id: str | None = None
    ) -> Chat | None:
        """Fetch a chat with all its messages eagerly loaded.

        Args:
            chat_id: Chat UUID string.
            user_id: If provided, returns None when the chat belongs to a different user.

        Returns:
            Chat instance with ``messages`` populated, or None.
        """

        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.messages))
        )
        chat = result.scalar_one_or_none()

        if not chat:
            return None

        if user_id and chat.user_id != user_id:
            return None

        return chat

    async def list_user_chats(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[tuple[Chat, ChatMessage | None]]:
        """List a user's chats ordered by most recently updated, with their last message.

        Args:
            user_id: UUID of the owning user.
            limit: Maximum number of chats to return.
            offset: Number of chats to skip for pagination.

        Returns:
            List of ``(Chat, last ChatMessage or None)`` tuples.
        """

        chats_result = await self.session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(desc(Chat.updated_at))
            .limit(limit)
            .offset(offset)
        )
        chats = list(chats_result.scalars())

        if not chats:
            return []

        chat_ids = [c.id for c in chats]
        last_msgs_result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id.in_(chat_ids))
            .distinct(ChatMessage.chat_id)
            .order_by(ChatMessage.chat_id, desc(ChatMessage.created_at))
        )
        last_msgs: dict[str, ChatMessage] = {
            m.chat_id: m for m in last_msgs_result.scalars()
        }
        return [(chat, last_msgs.get(chat.id)) for chat in chats]

    async def get_image_keys(self, chat_id: str) -> list[str]:
        """Return all MinIO image keys stored in user message payloads."""

        stmt = select(ChatMessage.payload).where(
            ChatMessage.chat_id == chat_id, ChatMessage.payload.isnot(None)
        )
        result = await self.session.execute(stmt)
        keys: list[str] = []

        for (payload,) in result:
            if isinstance(payload, dict) and payload.get("image_key"):
                keys.append(payload["image_key"])

        return keys

    async def delete_chat(self, chat_id: str, user_id: str | None = None) -> bool:
        """Delete a chat and return whether it existed and was accessible.

        Args:
            chat_id: Chat UUID string.
            user_id: If provided, only deletes if the chat belongs to this user.

        Returns:
            True if deleted, False if not found or forbidden.
        """

        chat = await self.get_chat(chat_id)

        if not chat:
            return False

        if user_id and chat.user_id != user_id:
            return False

        await self.session.delete(chat)
        await self.session.flush()
        return True

    async def add_message(
        self,
        chat_id: str,
        role: str,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """Append a message to a chat and update the chat ``updated_at`` timestamp.

        If ``role`` is ``"user"`` and the chat has no title yet, sets the title from ``content``.

        Args:
            chat_id: Chat UUID string.
            role: ``"user"`` or ``"assistant"``.
            message_type: ``"dialog"`` or ``"options"``.
            content: Plain text content of the message.
            payload: Optional JSON payload such as image key, VMS link, or event previews.

        Returns:
            Newly created ChatMessage instance.
        """

        message = ChatMessage(
            chat_id=chat_id,
            role=role,
            type=message_type,
            content=content,
            payload=payload,
        )
        self.session.add(message)
        await self.session.flush()
        chat = await self.get_chat(chat_id)

        if chat:
            chat.updated_at = datetime.now(timezone.utc)

            if role == "user" and not chat.title:
                chat.title = _build_chat_title(content)

            self.session.add(chat)

        await self.session.refresh(message)
        return message

    async def set_options_selected_ids(
        self, chat_id: str, resolution_id: str, selected_ids: list[str]
    ) -> list[str]:
        """Record the user's entity selection in an options message payload.

        Args:
            chat_id: Chat UUID string.
            resolution_id: Resolution message identifier stored in payload.
            selected_ids: IDs of the options the user selected.

        Returns:
            Display labels of the selected options for generating a user message.
        """

        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .where(ChatMessage.type == "options")
            .where(ChatMessage.payload["resolution_id"].astext == resolution_id)
        )
        msg = result.scalar_one_or_none()
        labels: list[str] = []

        if msg and msg.payload is not None:
            msg.payload = {**msg.payload, "selected_ids": selected_ids}
            self.session.add(msg)
            selected_set = {str(sid) for sid in selected_ids}
            labels = [
                opt["value"]
                for opt in msg.payload.get("options", [])
                if str(opt.get("id", "")) in selected_set
            ]

        return labels

    async def list_messages(self, chat_id: str) -> list[ChatMessage]:
        """Fetch all messages for a chat in chronological order.

        Args:
            chat_id: Chat UUID string.

        Returns:
            List of ChatMessage instances ordered by ``created_at``.
        """

        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars())
