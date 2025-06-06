"""Simple CLI for LocalDB operations."""
import click

logger = None


@click.group()
@click.pass_context
def main(ctx):
    """LocalDB - простое управление локальной базой данных."""
    ctx.ensure_object(dict)


@main.command("setup-user")
@click.argument('email')
@click.pass_context
def setup_user(ctx, email: str):
    """Настроить пользователя: создать запись и авторизоваться в Garmin Connect."""
    # Извлекаем user_id из email (часть до @)
    user_id = email.split('@')[0]
    
    try:
        import getpass
        from ...auth.client import AuthClient
        from ..core import LocalDBClient
        
        # 1. Запрашиваем пароль
        password = getpass.getpass(f"Пароль для {email} в Garmin Connect: ")
        
        # 2. Авторизуемся в Garmin Connect
        click.echo("🔐 Авторизация в Garmin Connect...")
        auth_client = AuthClient()
        
        result = auth_client.login(email, password)
        
        # Проверяем результат авторизации
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            click.echo("🔑 Требуется двухфакторная аутентификация")
            mfa_code = click.prompt("Введите код из приложения/SMS")
            result = auth_client.resume_login(mfa_code, result[1])
        
        # 3. Создаем или обновляем пользователя в локальной базе
        click.echo("💾 Сохранение данных пользователя...")
        with LocalDBClient("~/.garmy/health.db") as client:
            # Проверяем существует ли пользователь
            existing_user = client.get_user(user_id)
            if existing_user:
                click.echo(f"📝 Обновление существующего пользователя {user_id}")
                # Пользователь уже существует, просто обновляем информацию при необходимости
            else:
                click.echo(f"👤 Создание нового пользователя {user_id}")
                client.add_user(user_id, email)
            
        click.echo(f"✅ Пользователь {user_id} ({email}) успешно настроен!")
        click.echo(f"💡 Теперь можете синхронизировать данные: garmy-localdb sync {user_id}")
        
    except Exception as e:
        click.echo(f"✗ Ошибка настройки пользователя: {e}")
        if "Two-factor authentication" in str(e) or "MFA" in str(e):
            click.echo("💡 Возможно, у вас включена двухфакторная аутентификация.")
        elif "Invalid credentials" in str(e) or "login" in str(e).lower():
            click.echo("💡 Проверьте правильность email и пароля.")


@main.command("login")
@click.argument('user_id')
@click.pass_context
def login_user(ctx, user_id: str):
    """Повторно авторизовать существующего пользователя."""
    try:
        from ...auth.client import AuthClient
        from ..core import LocalDBClient
        import getpass
        
        # Проверяем существует ли пользователь
        with LocalDBClient("~/.garmy/health.db") as client:
            user = client.get_user(user_id)
            if not user:
                click.echo(f"✗ Пользователь {user_id} не найден")
                click.echo(f"💡 Создайте пользователя: garmy-localdb setup-user email@example.com")
                return
            
            email = user['email']
        
        # Запрашиваем пароль
        password = getpass.getpass(f"Пароль для {email} в Garmin Connect: ")
        
        # Авторизуемся
        click.echo("🔐 Авторизация в Garmin Connect...")
        auth_client = AuthClient()
        
        result = auth_client.login(email, password)
        
        # Проверяем результат авторизации
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            click.echo("🔑 Требуется двухфакторная аутентификация")
            mfa_code = click.prompt("Введите код из приложения/SMS")
            result = auth_client.resume_login(mfa_code, result[1])
            
        click.echo(f"✅ Пользователь {user_id} успешно авторизован!")
        
    except Exception as e:
        click.echo(f"✗ Ошибка авторизации: {e}")
        if "Two-factor authentication" in str(e) or "MFA" in str(e):
            click.echo("💡 Возможно, у вас включена двухфакторная аутентификация.")
        elif "Invalid credentials" in str(e) or "login" in str(e).lower():
            click.echo("💡 Проверьте правильность email и пароля.")


@main.command("status")
@click.argument('user_id')
@click.pass_context
def check_status(ctx, user_id: str):
    """Проверить статус авторизации пользователя."""
    try:
        from ...auth.client import AuthClient
        from ..core import LocalDBClient
        
        # Проверяем есть ли пользователь в базе
        with LocalDBClient("~/.garmy/health.db") as client:
            user = client.get_user(user_id)
            if not user:
                click.echo(f"✗ Пользователь {user_id} не найден в локальной базе")
                click.echo(f"💡 Создайте пользователя: garmy-localdb setup-user email@example.com")
                return
            
            click.echo(f"📋 Пользователь: {user['user_id']} ({user['email']})")
            
        # Проверяем авторизацию
        auth_client = AuthClient()
        if auth_client.is_authenticated:
            click.echo("✓ Авторизован в Garmin Connect")
        else:
            click.echo("✗ Не авторизован в Garmin Connect")
            click.echo(f"💡 Авторизуйтесь: garmy-localdb login {user_id}")
            
    except Exception as e:
        click.echo(f"✗ Ошибка: {e}")


@main.command("users")
@click.pass_context
def list_users(ctx):
    """Показать всех пользователей."""
    try:
        from ..core import LocalDBClient
        
        with LocalDBClient("~/.garmy/health.db") as client:
            users = client.list_users()
            if not users:
                click.echo("Пользователи не найдены")
                return
            
            click.echo("Пользователи:")
            for user in users:
                click.echo(f"  {user['user_id']} - {user['email']}")
    except Exception as e:
        click.echo(f"✗ Ошибка: {e}")


@main.command("sync")
@click.argument('user_id')
@click.argument('start_date', required=False)
@click.argument('end_date', required=False)
@click.option('--days', default=7, help='Количество дней для синхронизации (если не указаны даты)')
@click.option('--progress/--no-progress', default=True, help='Показывать прогресс')
@click.pass_context
def sync_data(ctx, user_id: str, start_date: str, end_date: str, days: int, progress: bool):
    """Синхронизировать данные пользователя."""
    try:
        from ..core import LocalDBClient
        from datetime import date, datetime, timedelta
        
        # Определяем диапазон дат
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            click.echo(f"Синхронизация данных для {user_id} с {start_date} по {end_date}...")
        else:
            end = date.today()
            start = end - timedelta(days=days-1)
            click.echo(f"Синхронизация данных для {user_id} за последние {days} дней...")
        
        progress_bar = None
        def progress_callback(sync_progress):
            nonlocal progress_bar
            if progress:
                if progress_bar is None:
                    try:
                        from tqdm import tqdm
                        progress_bar = tqdm(total=sync_progress.total_metrics, desc="Syncing metrics")
                    except ImportError:
                        # Fallback если tqdm не установлен
                        current = sync_progress.completed_metrics
                        total = sync_progress.total_metrics
                        percentage = (current / total * 100) if total > 0 else 0
                        click.echo(f"\r[{current}/{total}] {percentage:.1f}% {sync_progress.current_metric}", nl=False)
                        return
                
                # Обновляем прогрессбар
                progress_bar.n = sync_progress.completed_metrics
                progress_bar.set_postfix_str(f"{sync_progress.current_metric} | {sync_progress.current_date}")
                progress_bar.refresh()
        
        async def run_sync():
            with LocalDBClient("~/.garmy/health.db") as client:
                # Синхронизация с колбэком прогресса
                result = await client.sync_user_data(user_id, start, end, progress_callback if progress else None)
                
                # Закрываем прогрессбар
                if progress and progress_bar:
                    progress_bar.close()
                
                if isinstance(result, dict) and 'total_records' in result:
                    click.echo(f"✓ Синхронизировано {result['total_records']} записей")
                else:
                    click.echo("✓ Синхронизация завершена")
        
        import asyncio
        asyncio.run(run_sync())
                
    except Exception as e:
        click.echo(f"✗ Ошибка: {e}")


@main.command("stats")
@click.pass_context
def show_stats(ctx):
    """Показать статистику базы данных."""
    try:
        from ..core import LocalDBClient
        
        with LocalDBClient("~/.garmy/health.db") as client:
            stats = client.get_database_stats()
            
            click.echo("Статистика базы данных:")
            click.echo(f"  Пользователи: {stats.get('users', 0)}")
            click.echo(f"  Всего записей: {stats.get('total_records', 0)}")
            
            if 'metrics' in stats:
                click.echo("  Метрики:")
                for metric, count in stats['metrics'].items():
                    click.echo(f"    {metric}: {count}")
                    
    except Exception as e:
        click.echo(f"✗ Ошибка: {e}")


if __name__ == '__main__':
    main()
