"""
Система отображения прогресса синхронизации.
Поддерживает различные типы вывода: логи, progress bars, JSON и другие.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    from rich.console import Console
    from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ProgressEventType(Enum):
    """Типы событий прогресса."""
    SYNC_START = "sync_start"
    SYNC_END = "sync_end" 
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    BATCH_PROGRESS = "batch_progress"
    METRIC_SYNCED = "metric_synced"
    ACTIVITY_SYNCED = "activity_synced"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ProgressEvent:
    """Событие прогресса синхронизации."""
    event_type: ProgressEventType
    message: str
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['event_type'] = self.event_type.value
        return result


@dataclass
class SyncStats:
    """Статистика синхронизации."""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    current_task: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def processed(self) -> int:
        """Всего обработано задач."""
        return self.completed + self.failed + self.skipped
    
    @property
    def progress_percentage(self) -> float:
        """Процент выполнения."""
        return (self.processed / self.total_tasks * 100) if self.total_tasks > 0 else 0
    
    @property
    def elapsed_time(self) -> float:
        """Время выполнения в секундах."""
        if not self.start_time:
            return 0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Оценка времени до завершения."""
        if self.processed == 0 or self.elapsed_time == 0:
            return None
        
        remaining_tasks = self.total_tasks - self.processed
        avg_task_time = self.elapsed_time / self.processed
        return remaining_tasks * avg_task_time


class ProgressReporter(ABC):
    """Абстрактный репортер прогресса."""
    
    def __init__(self, name: str = "sync"):
        self.name = name
        self.stats = SyncStats()
        self.events: List[ProgressEvent] = []
    
    def emit_event(self, event_type: ProgressEventType, message: str, **data):
        """Отправка события."""
        event = ProgressEvent(
            event_type=event_type,
            message=message,
            timestamp=datetime.now(),
            data=data
        )
        self.events.append(event)
        self._handle_event(event)
    
    @abstractmethod
    def _handle_event(self, event: ProgressEvent):
        """Обработка события (должна быть реализована в подклассе)."""
        pass
    
    def start_sync(self, total_tasks: int, description: str = ""):
        """Начало синхронизации."""
        self.stats.total_tasks = total_tasks
        self.stats.start_time = datetime.now()
        self.emit_event(ProgressEventType.SYNC_START, f"Starting sync: {description}", 
                       total_tasks=total_tasks, description=description)
    
    def end_sync(self, success: bool = True):
        """Окончание синхронизации."""
        self.stats.end_time = datetime.now()
        status = "completed" if success else "failed"
        self.emit_event(ProgressEventType.SYNC_END, f"Sync {status}", 
                       success=success, stats=asdict(self.stats))
    
    def task_start(self, task_name: str, details: str = ""):
        """Начало задачи."""
        self.stats.current_task = task_name
        self.emit_event(ProgressEventType.TASK_START, f"Starting: {task_name}", 
                       task_name=task_name, details=details)
    
    def task_complete(self, task_name: str, details: str = ""):
        """Завершение задачи."""
        self.stats.completed += 1
        self.emit_event(ProgressEventType.TASK_COMPLETE, f"Completed: {task_name}", 
                       task_name=task_name, details=details)
    
    def task_failed(self, task_name: str, error: str = ""):
        """Ошибка в задаче."""
        self.stats.failed += 1
        self.emit_event(ProgressEventType.TASK_FAILED, f"Failed: {task_name}", 
                       task_name=task_name, error=error)
    
    def task_skipped(self, task_name: str, reason: str = ""):
        """Пропуск задачи."""
        self.stats.skipped += 1
        self.emit_event(ProgressEventType.TASK_SKIPPED, f"Skipped: {task_name}", 
                       task_name=task_name, reason=reason)
    
    def metric_synced(self, metric_type: str, date: str, records: int):
        """Синхронизирована метрика."""
        self.emit_event(ProgressEventType.METRIC_SYNCED, f"Synced {metric_type} for {date}", 
                       metric_type=metric_type, date=date, records=records)
    
    def activity_synced(self, date: str, count: int):
        """Синхронизированы активности."""
        self.emit_event(ProgressEventType.ACTIVITY_SYNCED, f"Synced {count} activities for {date}", 
                       date=date, count=count)
    
    def error(self, message: str, **data):
        """Ошибка."""
        self.emit_event(ProgressEventType.ERROR, message, **data)
    
    def warning(self, message: str, **data):
        """Предупреждение."""
        self.emit_event(ProgressEventType.WARNING, message, **data)
    
    def info(self, message: str, **data):
        """Информация."""
        self.emit_event(ProgressEventType.INFO, message, **data)


class LoggingReporter(ProgressReporter):
    """Репортер через стандартное логирование."""
    
    def __init__(self, name: str = "sync", logger: Optional[logging.Logger] = None, 
                 log_level: int = logging.INFO, show_progress: bool = True):
        super().__init__(name)
        self.logger = logger or logging.getLogger(f"{__name__}.{name}")
        self.log_level = log_level
        self.show_progress = show_progress
        self._last_progress_log = 0
        self._progress_interval = 10  # Логировать прогресс каждые 10 задач
    
    def _handle_event(self, event: ProgressEvent):
        """Обработка через логирование."""
        level_map = {
            ProgressEventType.ERROR: logging.ERROR,
            ProgressEventType.WARNING: logging.WARNING,
            ProgressEventType.TASK_FAILED: logging.WARNING,
        }
        
        log_level = level_map.get(event.event_type, self.log_level)
        
        # Добавляем контекст для некоторых событий
        message = event.message
        if event.event_type == ProgressEventType.SYNC_START:
            message = f"🚀 {message}"
        elif event.event_type == ProgressEventType.SYNC_END:
            elapsed = self.stats.elapsed_time
            message = f"✅ {message} in {elapsed:.1f}s - {self.stats.completed} success, {self.stats.failed} failed, {self.stats.skipped} skipped"
        elif event.event_type == ProgressEventType.TASK_COMPLETE and self.show_progress:
            # Логируем прогресс периодически
            if self.stats.processed - self._last_progress_log >= self._progress_interval:
                progress = self.stats.progress_percentage
                eta = self.stats.eta_seconds
                eta_str = f", ETA: {eta:.0f}s" if eta else ""
                message = f"📊 Progress: {self.stats.processed}/{self.stats.total_tasks} ({progress:.1f}%){eta_str}"
                self._last_progress_log = self.stats.processed
            else:
                return  # Не логируем каждую задачу
        
        self.logger.log(log_level, message)


class TqdmReporter(ProgressReporter):
    """Репортер через tqdm progress bar."""
    
    def __init__(self, name: str = "sync", leave: bool = True, 
                 show_details: bool = True, update_interval: float = 0.1):
        super().__init__(name)
        if not TQDM_AVAILABLE:
            raise ImportError("tqdm is required for TqdmReporter. Install with: pip install tqdm")
        
        self.leave = leave
        self.show_details = show_details
        self.update_interval = update_interval
        self.pbar: Optional[tqdm] = None
        self._last_update = 0
    
    def _handle_event(self, event: ProgressEvent):
        """Обработка через tqdm."""
        if event.event_type == ProgressEventType.SYNC_START:
            self.pbar = tqdm(
                total=self.stats.total_tasks,
                desc=f"🔄 {self.name}",
                leave=self.leave,
                unit="task"
            )
        
        elif event.event_type == ProgressEventType.SYNC_END and self.pbar:
            self.pbar.close()
        
        elif event.event_type in [ProgressEventType.TASK_COMPLETE, ProgressEventType.TASK_FAILED, ProgressEventType.TASK_SKIPPED]:
            if self.pbar:
                # Обновляем прогресс
                self.pbar.update(1)
                
                # Обновляем описание, если нужно
                if self.show_details and time.time() - self._last_update > self.update_interval:
                    progress = self.stats.progress_percentage
                    desc = f"🔄 {self.name} ({progress:.1f}%)"
                    if self.stats.current_task:
                        desc += f" - {self.stats.current_task}"
                    self.pbar.set_description(desc)
                    self._last_update = time.time()
        
        elif event.event_type == ProgressEventType.ERROR and self.pbar:
            self.pbar.write(f"❌ Error: {event.message}")
        
        elif event.event_type == ProgressEventType.WARNING and self.pbar:
            self.pbar.write(f"⚠️ Warning: {event.message}")


class RichReporter(ProgressReporter):
    """Репортер через Rich (красивый терминальный вывод)."""
    
    def __init__(self, name: str = "sync", show_details: bool = True, 
                 show_stats_table: bool = True):
        super().__init__(name)
        if not RICH_AVAILABLE:
            raise ImportError("rich is required for RichReporter. Install with: pip install rich")
        
        self.console = Console()
        self.show_details = show_details
        self.show_stats_table = show_stats_table
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None
        self.live: Optional[Live] = None
    
    def _handle_event(self, event: ProgressEvent):
        """Обработка через Rich."""
        if event.event_type == ProgressEventType.SYNC_START:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("({task.percentage:>3.0f}%)"),
                TimeElapsedColumn(),
                console=self.console
            )
            
            self.task_id = self.progress.add_task(
                f"🔄 {self.name}",
                total=self.stats.total_tasks
            )
            
            if self.show_stats_table:
                self.live = Live(self._create_layout(), console=self.console, refresh_per_second=2)
                self.live.start()
            else:
                self.progress.start()
        
        elif event.event_type == ProgressEventType.SYNC_END:
            if self.live:
                self.live.stop()
            elif self.progress:
                self.progress.stop()
            
            # Финальное сообщение
            status = "✅ Completed" if event.data.get('success', True) else "❌ Failed"
            elapsed = self.stats.elapsed_time
            self.console.print(f"{status} in {elapsed:.1f}s - {self.stats.completed} success, {self.stats.failed} failed, {self.stats.skipped} skipped")
        
        elif event.event_type in [ProgressEventType.TASK_COMPLETE, ProgressEventType.TASK_FAILED, ProgressEventType.TASK_SKIPPED]:
            if self.progress and self.task_id is not None:
                self.progress.update(self.task_id, advance=1)
                
                if self.show_details and self.stats.current_task:
                    desc = f"🔄 {self.name} - {self.stats.current_task}"
                    self.progress.update(self.task_id, description=desc)
        
        elif event.event_type == ProgressEventType.ERROR:
            self.console.print(f"❌ [red]Error:[/red] {event.message}")
        
        elif event.event_type == ProgressEventType.WARNING:
            self.console.print(f"⚠️ [yellow]Warning:[/yellow] {event.message}")
    
    def _create_layout(self):
        """Создание лэйаута с таблицей статистики."""
        if not self.progress:
            return Table()
        
        # Основной прогресс
        progress_panel = self.progress
        
        # Таблица статистики
        stats_table = Table(title="📊 Sync Statistics", show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")
        
        stats_table.add_row("✅ Completed", str(self.stats.completed))
        stats_table.add_row("❌ Failed", str(self.stats.failed))
        stats_table.add_row("⏭️ Skipped", str(self.stats.skipped))
        stats_table.add_row("⏱️ Elapsed", f"{self.stats.elapsed_time:.1f}s")
        
        if self.stats.eta_seconds:
            stats_table.add_row("🔮 ETA", f"{self.stats.eta_seconds:.1f}s")
        
        # Компонуем все вместе
        from rich.columns import Columns
        return Columns([progress_panel, stats_table])


class JsonReporter(ProgressReporter):
    """Репортер в JSON формат (для машинной обработки)."""
    
    def __init__(self, name: str = "sync", output_file: Optional[str] = None, 
                 real_time: bool = False):
        super().__init__(name)
        self.output_file = output_file
        self.real_time = real_time  # Писать события в реальном времени
    
    def _handle_event(self, event: ProgressEvent):
        """Обработка через JSON вывод."""
        event_dict = event.to_dict()
        event_dict['stats'] = asdict(self.stats)
        
        if self.real_time:
            if self.output_file:
                # Добавляем в файл
                with open(self.output_file, 'a') as f:
                    json.dump(event_dict, f, ensure_ascii=False)
                    f.write('\n')
            else:
                # Выводим в stdout
                print(json.dumps(event_dict, ensure_ascii=False))
    
    def end_sync(self, success: bool = True):
        """Окончание синхронизации с сохранением полного отчета."""
        super().end_sync(success)
        
        if not self.real_time and self.output_file:
            # Сохраняем полный отчет в конце
            report = {
                'sync_name': self.name,
                'stats': asdict(self.stats),
                'events': [event.to_dict() for event in self.events],
                'summary': {
                    'success': success,
                    'total_events': len(self.events),
                    'duration_seconds': self.stats.elapsed_time
                }
            }
            
            with open(self.output_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)


class MultiReporter(ProgressReporter):
    """Репортер, объединяющий несколько репортеров."""
    
    def __init__(self, name: str = "sync", reporters: List[ProgressReporter] = None):
        super().__init__(name)
        self.reporters = reporters or []
        
        # Синхронизируем статистику между репортерами
        for reporter in self.reporters:
            reporter.stats = self.stats
    
    def add_reporter(self, reporter: ProgressReporter):
        """Добавление репортера."""
        reporter.stats = self.stats
        self.reporters.append(reporter)
    
    def _handle_event(self, event: ProgressEvent):
        """Обработка через все репортеры."""
        for reporter in self.reporters:
            try:
                reporter._handle_event(event)
            except Exception as e:
                # Не падаем, если один из репортеров сломался
                print(f"Warning: Reporter {type(reporter).__name__} failed: {e}")


class SilentReporter(ProgressReporter):
    """Тихий репортер (ничего не выводит)."""
    
    def _handle_event(self, event: ProgressEvent):
        """Ничего не делаем."""
        pass


# Фабрика для создания репортеров
def create_reporter(reporter_type: str, **kwargs) -> ProgressReporter:
    """Фабрика для создания репортеров."""
    
    if reporter_type == "logging":
        return LoggingReporter(**kwargs)
    elif reporter_type == "tqdm":
        if not TQDM_AVAILABLE:
            raise ImportError("tqdm is required. Install with: pip install tqdm")
        return TqdmReporter(**kwargs)
    elif reporter_type == "rich":
        if not RICH_AVAILABLE:
            raise ImportError("rich is required. Install with: pip install rich")
        return RichReporter(**kwargs)
    elif reporter_type == "json":
        return JsonReporter(**kwargs)
    elif reporter_type == "silent":
        return SilentReporter(**kwargs)
    else:
        raise ValueError(f"Unknown reporter type: {reporter_type}")