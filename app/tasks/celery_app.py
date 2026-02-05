"""
Celery 애플리케이션 설정
비동기 작업 처리를 위한 Celery 앱
"""
from celery import Celery
from kombu import Exchange, Queue

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Celery 앱 생성
celery_app = Celery(
    "dasystem",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery 설정
celery_app.conf.update(
    # 직렬화
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 타임존
    timezone="Asia/Seoul",
    enable_utc=True,

    # 작업 추적
    task_track_started=True,
    task_send_sent_event=True,

    # 타임아웃
    task_time_limit=7200,  # 2시간
    task_soft_time_limit=6600,  # 1시간 50분

    # 결과 만료
    result_expires=3600,  # 1시간

    # 워커 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나의 작업만
    worker_max_tasks_per_child=50,  # 메모리 누수 방지

    # 재시도
    task_acks_late=True,  # 작업 완료 후 ack
    task_reject_on_worker_lost=True,

    # 동시성 (Windows 환경)
    # Windows에서는 eventlet 또는 gevent 사용 권장
    worker_pool="solo",  # Windows 기본값

    # 큐 설정
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("data_processing", Exchange("data"), routing_key="data.#"),
        Queue("modeling", Exchange("modeling"), routing_key="modeling.#"),
        Queue("research", Exchange("research"), routing_key="research.#"),
        Queue("reporting", Exchange("reporting"), routing_key="reporting.#"),
    ),

    # 라우팅
    task_routes={
        "app.tasks.data_tasks.*": {"queue": "data_processing"},
        "app.tasks.modeling_tasks.*": {"queue": "modeling"},
        "app.tasks.research_tasks.*": {"queue": "research"},
        "app.tasks.report_tasks.*": {"queue": "reporting"},
    },
)


# 태스크 자동 발견
celery_app.autodiscover_tasks([
    "app.tasks.data_tasks",
    "app.tasks.modeling_tasks",
    "app.tasks.research_tasks",
    "app.tasks.report_tasks",
])


# Celery 시그널 핸들러
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """주기적 작업 설정 (필요시)"""
    # 예: 매일 자정에 오래된 파일 정리
    # sender.add_periodic_task(
    #     crontab(hour=0, minute=0),
    #     cleanup_old_files.s(),
    # )
    pass


@celery_app.task(bind=True)
def debug_task(self):
    """디버그용 테스트 태스크"""
    logger.info("debug_task_called", request=self.request)
    return {
        "task_id": self.request.id,
        "task_name": self.name,
        "message": "Celery is working!"
    }


if __name__ == "__main__":
    # Celery 워커 시작 (개발용)
    # 실제로는 커맨드라인에서 실행: celery -A app.tasks.celery_app worker
    celery_app.start()
