# 📊 Garmy LocalDB - Руководство пользователя

Полное руководство по использованию модуля локальной базы данных для синхронизации и хранения данных Garmin Connect.

## 🚀 Установка

```bash
# Установка с поддержкой локальной базы данных
pip install garmy[localdb]
```

## 🔧 Первоначальная настройка

### 1. Настройка пользователя

Первым шагом необходимо добавить ваш аккаунт Garmin Connect:

```bash
garmy-localdb setup-user your-email@gmail.com --name "Ваше Имя"
```

**Что происходит:**
- Система запросит пароль от Garmin Connect
- Пройдет аутентификация и сохранит токены в `~/.garmy/`
- Создаст пользователя в локальной SQLite базе
- User ID будет автоматически сгенерирован из email (например: `sergei_o_belousov_stuff_gmail_com`)

### 2. Проверка настроенных пользователей

```bash
garmy-localdb list-users
```

Покажет таблицу с информацией о всех настроенных пользователях.

## 📊 Синхронизация данных

### Базовая синхронизация

```bash
# Синхронизация всех метрик за период (по умолчанию: новые даты → старые)
garmy-localdb sync user_id 2024-01-01 2024-12-31

# Пример с реальным user_id
garmy-localdb sync sergei_o_belousov_stuff_gmail_com 2024-01-01 2024-12-31

# Прямой хронологический порядок (старые даты → новые)
garmy-localdb sync user_id 2024-01-01 2024-12-31 --chronological
```

### Синхронизация конкретных метрик

```bash
# Только данные о сне и пульсе
garmy-localdb sync user_id 2024-11-01 2024-11-30 --metrics sleep heart_rate

# Только шаги за последнюю неделю
garmy-localdb sync user_id 2024-12-01 2024-12-07 --metrics steps
```

### Фоновая синхронизация

```bash
# Запуск синхронизации в фоне (не блокирует терминал)
garmy-localdb sync user_id 2024-01-01 2024-12-31 --background

# Синхронизация с настройкой размера батча
garmy-localdb sync user_id 2024-01-01 2024-12-31 --batch-size 30 --background

# Хронологический порядок для архивных данных
garmy-localdb sync user_id 2020-01-01 2023-12-31 --chronological --background
```

### Порядок синхронизации

**По умолчанию (рекомендуется): Обратная хронология** 🔄
- Синхронизация идет от новых дат к старым
- Сначала получаете самые актуальные данные
- Удобно для ежедневного использования
- Можно прервать и уже иметь свежие данные

```bash
# По умолчанию: 2024-12-31 → 2024-12-30 → ... → 2024-01-01
garmy-localdb sync user_id 2024-01-01 2024-12-31
```

**Прямая хронология:** ⏩
- Синхронизация идет от старых дат к новым  
- Подходит для архивирования исторических данных
- Полезно для аналитики по временным рядам

```bash
# С флагом --chronological: 2024-01-01 → 2024-01-02 → ... → 2024-12-31
garmy-localdb sync user_id 2024-01-01 2024-12-31 --chronological
```

## 📋 Доступные метрики

| Метрика | Описание |
|---------|----------|
| `sleep` | Анализ сна (фазы, SpO2, эффективность) |
| `heart_rate` | Данные пульса (дневные сводки, непрерывные данные) |
| `body_battery` | Уровень энергии Body Battery |
| `stress` | Уровень стресса на основе HRV |
| `hrv` | Вариабельность сердечного ритма |
| `respiration` | Данные о дыхании |
| `training_readiness` | Готовность к тренировкам |
| `activities` | Активности и тренировки |
| `steps` | Шаги и движение |
| `calories` | Сожженные калории |
| `daily_summary` | Ежедневная сводка здоровья |

## 📈 Мониторинг синхронизации

### Просмотр статуса

```bash
# Статус всех активных синхронизаций
garmy-localdb status

# Статус конкретной синхронизации (используйте ID из вывода предыдущей команды)
garmy-localdb status 5a36d0e0-00cf-4c5c-9499-aabc08d90605
```

### Управление синхронизацией

```bash
# Поставить на паузу
garmy-localdb pause <sync_id>

# Возобновить
garmy-localdb resume <sync_id>

# Полностью остановить
garmy-localdb stop <sync_id>
```

## 🔍 Работа с данными

### Просмотр данных

```bash
# Просмотр данных о сне (последние 10 дат)
garmy-localdb query user_id sleep

# Данные за конкретный период
garmy-localdb query user_id heart_rate --start-date 2024-11-01 --end-date 2024-11-30

# Все доступные данные по шагам
garmy-localdb query user_id steps
```

### Экспорт в JSON

```bash
# Экспорт данных о сне в JSON
garmy-localdb query user_id sleep --format json

# Экспорт за период и сохранение в файл
garmy-localdb query user_id sleep --format json --start-date 2024-12-01 > sleep_data.json

# Экспорт всех активностей за год
garmy-localdb query user_id activities --format json --start-date 2024-01-01 --end-date 2024-12-31 > activities_2024.json
```

## 📊 Статистика и управление

### Статистика базы данных

```bash
garmy-localdb stats
```

Показывает:
- Путь к базе данных
- Количество пользователей
- Количество записей для каждого пользователя
- Состояние сжатия

### Управление пользователями

```bash
# Удалить пользователя и все его данные
garmy-localdb remove-user user_id

# Удалить без подтверждения
garmy-localdb remove-user user_id --yes
```

## 🛠️ Расширенные возможности

### Кастомный путь к базе

```bash
# Использование базы в другом месте
garmy-localdb --db-path /path/to/custom/db stats
garmy-localdb --db-path /path/to/custom/db list-users
```

### Многопользовательская настройка

```bash
# Добавить несколько аккаунтов
garmy-localdb setup-user user1@gmail.com --name "Пользователь 1"
garmy-localdb setup-user user2@gmail.com --name "Пользователь 2"

# Синхронизация для разных пользователей
garmy-localdb sync user1_gmail_com 2024-01-01 2024-12-31 --background
garmy-localdb sync user2_gmail_com 2024-01-01 2024-12-31 --background

# Просмотр данных конкретного пользователя
garmy-localdb query user1_gmail_com sleep
garmy-localdb query user2_gmail_com heart_rate
```

## 📝 Практические примеры

### Ежедневная синхронизация

```bash
#!/bin/bash
# Скрипт для ежедневной синхронизации последних 7 дней

USER_ID="your_email_gmail_com"
START_DATE=$(date -d '7 days ago' +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

garmy-localdb sync $USER_ID $START_DATE $END_DATE --background

echo "Синхронизация запущена для периода $START_DATE - $END_DATE"
```

### Полная архивация данных

```bash
#!/bin/bash
# Скрипт для создания полного архива данных за год

USER_ID="your_email_gmail_com"
YEAR="2024"
EXPORT_DIR="garmin_export_$YEAR"

mkdir -p $EXPORT_DIR

# Экспорт всех метрик
metrics=("sleep" "heart_rate" "body_battery" "stress" "hrv" "respiration" "training_readiness" "activities" "steps" "calories" "daily_summary")

for metric in "${metrics[@]}"; do
    echo "Экспортируем $metric..."
    garmy-localdb query $USER_ID $metric --format json --start-date $YEAR-01-01 --end-date $YEAR-12-31 > "$EXPORT_DIR/${metric}.json"
done

echo "Экспорт завершен в папке $EXPORT_DIR"
```

### Мониторинг длительной синхронизации

```bash
#!/bin/bash
# Запуск синхронизации за несколько лет с мониторингом

USER_ID="your_email_gmail_com"

# Запуск синхронизации в фоне
garmy-localdb sync $USER_ID 2020-01-01 2024-12-31 --background

# Получение sync_id из последнего запуска
SYNC_ID=$(garmy-localdb status | grep "Sync ID" | tail -1 | awk '{print $3}')

echo "Sync ID: $SYNC_ID"
echo "Мониторинг прогресса каждые 30 секунд..."

# Мониторинг прогресса
while true; do
    clear
    echo "=== Статус синхронизации $(date) ==="
    garmy-localdb status $SYNC_ID
    sleep 30
done
```

## 🗂️ Структура файлов

```
~/.garmy/
├── localdb/
│   ├── garmin_data.db          # SQLite база данных
│   └── config.json             # Конфигурация базы
├── oauth1_token.json           # OAuth1 токены
└── oauth2_token.json           # OAuth2 токены
```

## ⚡ Особенности и ограничения

### Производительность
- SQLite с WAL режимом для конкурентного доступа
- Batch обработка по 50 дней (настраивается)
- Автоматические checkpoint'ы каждую минуту
- Проверка целостности данных с SHA256

### Восстановление после сбоев
- ✅ Автоматическое возобновление прерванной синхронизации
- ✅ Checkpoint'ы для crash recovery  
- ✅ Retry логика с экспоненциальной задержкой
- ✅ Транзакционная безопасность

### Ограничения API
- Garmin может ограничивать частоту запросов
- Некоторые старые данные могут быть недоступны
- MFA аутентификация поддерживается

## 🆘 Решение проблем

### Проблемы с аутентификацией

```bash
# Повторная аутентификация
garmy-localdb setup-user your-email@gmail.com --name "Your Name"

# Проверка пользователей
garmy-localdb list-users
```

### Проблемы с синхронизацией

```bash
# Проверка статуса всех синхронизаций
garmy-localdb status

# Остановка зависшей синхронизации
garmy-localdb stop <sync_id>

# Запуск с меньшим batch размером
garmy-localdb sync user_id 2024-01-01 2024-01-31 --batch-size 10
```

### Проблемы с базой данных

```bash
# Проверка статистики базы
garmy-localdb stats

# Использование другого пути к базе
garmy-localdb --db-path /tmp/garmin_test.db stats
```

### Логи и отладка

```bash
# Запуск с подробным выводом (если доступно)
garmy-localdb sync user_id 2024-12-01 2024-12-02 --metrics sleep

# Проверка содержимого базы
garmy-localdb query user_id sleep --start-date 2024-12-01 --end-date 2024-12-01
```

## 🎯 Рекомендации по использованию

1. **Начните с малого**: Сначала синхронизируйте небольшой период (неделя-месяц)
2. **Используйте фоновый режим**: Для больших периодов всегда используйте `--background`
3. **Регулярные бэкапы**: Периодически делайте экспорт важных данных в JSON
4. **Мониторинг**: Проверяйте статус длительных синхронизаций
5. **Пошаговый подход**: Синхронизируйте по годам, а не все сразу

Теперь вы готовы эффективно использовать Garmy LocalDB для работы с вашими данными Garmin Connect! 🏃‍♂️📊