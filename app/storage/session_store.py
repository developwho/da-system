"""
Redis 기반 세션 스토어
대화 상태 및 분석 작업 세션을 관리합니다.
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis
from redis import Redis

from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import DasystemException

logger = get_logger(__name__)


class SessionNotFoundError(DasystemException):
    """세션을 찾을 수 없음"""
    pass


class SessionStore:
    """Redis 기반 세션 스토어"""

    def __init__(self, redis_url: str = None):
        """
        세션 스토어 초기화

        Args:
            redis_url: Redis 연결 URL (기본값: settings.REDIS_URL)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        try:
            self.redis_client: Redis = redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            # 연결 테스트
            self.redis_client.ping()
            logger.info("redis_connected", url=self.redis_url)
        except redis.ConnectionError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    def create_session(
        self,
        session_id: str,
        initial_data: Dict[str, Any] = None,
        ttl: int = 86400  # 24시간
    ) -> Dict[str, Any]:
        """
        새 세션 생성

        Args:
            session_id: 세션 ID
            initial_data: 초기 데이터
            ttl: Time-To-Live (초)

        Returns:
            생성된 세션 데이터
        """
        session_data = {
            "session_id": session_id,
            "state": "initialized",
            "context": initial_data or {},
            "history": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        key = self._get_session_key(session_id)
        self.redis_client.setex(
            key,
            ttl,
            json.dumps(session_data, ensure_ascii=False)
        )

        logger.info("session_created", session_id=session_id, ttl=ttl)
        return session_data

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터

        Raises:
            SessionNotFoundError: 세션이 존재하지 않음
        """
        key = self._get_session_key(session_id)
        data = self.redis_client.get(key)

        if data is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        session_data = json.loads(data)
        logger.debug("session_retrieved", session_id=session_id)
        return session_data

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any],
        extend_ttl: bool = True
    ) -> Dict[str, Any]:
        """
        세션 업데이트

        Args:
            session_id: 세션 ID
            updates: 업데이트할 데이터
            extend_ttl: TTL 연장 여부

        Returns:
            업데이트된 세션 데이터
        """
        def apply_updates(data: Dict[str, Any]) -> Dict[str, Any]:
            data.update(updates)
            return data

        session_data = self._update_session_atomic(
            session_id=session_id,
            update_fn=apply_updates,
            extend_ttl=extend_ttl
        )

        logger.debug("session_updated", session_id=session_id)
        return session_data

    def update_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        세션 컨텍스트 업데이트

        Args:
            session_id: 세션 ID
            context_updates: 컨텍스트 업데이트

        Returns:
            업데이트된 세션 데이터
        """
        def apply_context_update(data: Dict[str, Any]) -> Dict[str, Any]:
            data.setdefault("context", {})
            data["context"].update(context_updates)
            return data

        return self._update_session_atomic(
            session_id=session_id,
            update_fn=apply_context_update
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        대화 메시지 추가

        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user, assistant, system)
            content: 메시지 내용
            metadata: 추가 메타데이터

        Returns:
            업데이트된 세션 데이터
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        def apply_message_update(data: Dict[str, Any]) -> Dict[str, Any]:
            data.setdefault("history", [])
            data["history"].append(message)
            return data

        return self._update_session_atomic(
            session_id=session_id,
            update_fn=apply_message_update
        )

    def get_history(
        self,
        session_id: str,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        대화 기록 조회

        Args:
            session_id: 세션 ID
            limit: 최대 메시지 수

        Returns:
            메시지 리스트
        """
        session_data = self.get_session(session_id)
        history = session_data.get("history", [])

        if limit:
            return history[-limit:]
        return history

    def _update_session_atomic(
        self,
        session_id: str,
        update_fn,
        extend_ttl: bool = True,
        ttl: int = 86400,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """세션 업데이트를 원자적으로 수행"""
        key = self._get_session_key(session_id)
        for _ in range(max_retries):
            with self.redis_client.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    data = pipe.get(key)
                    if data is None:
                        raise SessionNotFoundError(f"Session not found: {session_id}")

                    session_data = json.loads(data)
                    session_data = update_fn(session_data) or session_data
                    session_data["updated_at"] = datetime.now().isoformat()

                    payload = json.dumps(session_data, ensure_ascii=False)
                    pipe.multi()
                    if extend_ttl:
                        pipe.setex(key, ttl, payload)
                    else:
                        pipe.set(key, payload, keepttl=True)
                    pipe.execute()
                    return session_data
                except redis.WatchError:
                    continue

        raise DasystemException("Failed to update session due to concurrent modifications")

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        key = self._get_session_key(session_id)
        result = self.redis_client.delete(key)
        logger.info("session_deleted", session_id=session_id)
        return result > 0

    def list_sessions(
        self,
        pattern: str = "*",
        limit: int = 100
    ) -> List[str]:
        """
        세션 목록 조회

        Args:
            pattern: 세션 ID 패턴
            limit: 최대 개수

        Returns:
            세션 ID 리스트
        """
        full_pattern = f"session:{pattern}"
        keys = []

        for key in self.redis_client.scan_iter(match=full_pattern, count=limit):
            session_id = key.replace("session:", "")
            keys.append(session_id)

        return keys[:limit]

    def session_exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인

        Args:
            session_id: 세션 ID

        Returns:
            존재 여부
        """
        key = self._get_session_key(session_id)
        return self.redis_client.exists(key) > 0

    def get_ttl(self, session_id: str) -> int:
        """
        세션 TTL 조회

        Args:
            session_id: 세션 ID

        Returns:
            남은 TTL (초), -1: 만료 없음, -2: 키 없음
        """
        key = self._get_session_key(session_id)
        return self.redis_client.ttl(key)

    def extend_ttl(self, session_id: str, ttl: int = 86400) -> bool:
        """
        세션 TTL 연장

        Args:
            session_id: 세션 ID
            ttl: 새 TTL (초)

        Returns:
            성공 여부
        """
        key = self._get_session_key(session_id)
        return self.redis_client.expire(key, ttl)

    @staticmethod
    def _get_session_key(session_id: str) -> str:
        """세션 키 생성"""
        return f"session:{session_id}"

    def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("redis_connection_closed")


# 전역 세션 스토어 인스턴스 (싱글톤)
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """
    세션 스토어 인스턴스 가져오기 (싱글톤)

    Returns:
        SessionStore 인스턴스
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
