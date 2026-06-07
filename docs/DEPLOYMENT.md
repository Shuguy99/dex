# Развёртывание Dex

## Минимальные требования

| Компонент       | Минимум              | Рекомендуется        |
|----------------|----------------------|----------------------|
| CPU            | 4 ядра, x86_64       | 8+ ядер              |
| RAM            | 8 ГБ                 | 32 ГБ                |
| GPU            | Не требуется*        | 12+ ГБ VRAM          |
| Диск           | 10 ГБ                | 50+ ГБ               |
| ОС             | Windows 10/11        | Windows 11           |
| Python         | 3.12+                | 3.12+                |

*Без GPU — только rule-based режим и крошечные модели (Qwen2.5:0.5b)

## Быстрый старт

### 1. Установка Python

```powershell
# Скачать Python 3.12+ с https://python.org
# При установке ОБЯЗАТЕЛЬНО отметить "Add Python to PATH"
python --version  # Проверка
```

### 2. Установка Ollama

```powershell
# Скачать с https://ollama.com/download/windows
# Установить, запустить
ollama pull qwen2.5:14b    # Основная модель
ollama pull deepseek-coder-v2  # Для кода
ollama pull llama3.2:3b    # Лёгкая (опционально)
```

### 3. Установка Dex

```powershell
git clone <repo> dex
cd dex
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install ollama python-dotenv requests
```

### 4. Запуск

```powershell
# CLI режим
python main.py

# С голосом
python main.py --voice

# Windows GUI
python main.py --dashboard

# Qwen2.5:14b (рекомендуется)
ollama run qwen2.5:14b
```

### 5. Проверка

```powershell
# Убедиться, что Ollama работает
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3).read())"

# Запустить тесты
set DEX_SKIP_LLM=1
pytest tests/ -v
```

## Переменные окружения

| Переменная       | Значение по умолч. | Описание                          |
|-----------------|--------------------|-----------------------------------|
| `DEX_SKIP_LLM`  | (нет)              | Если =1, пропустить проверку Ollama|
| `OLLAMA_HOST`   | `localhost:11434`  | Адрес Ollama сервера              |
| `DEX_CONFIG`    | `config.py`        | Путь к файлу конфигурации         |
| `DEX_DATA_DIR`  | `./data`           | Директория для данных              |

## Конфигурация

Основные настройки в `config.py`. Ключевые флаги:

```python
DASHBOARD_ENABLED = True     # GUI
VOICE_ENABLED = False        # Голосовой ввод/вывод
CAMERA_ENABLED = False       # Камера
GESTURE_ENABLED = False      # Жесты (MediaPipe)
MESH_ENABLED = False         # P2P-сеть
WEARABLE_ENABLED = False     # Носимые устройства
```

Все модули с внешними зависимостями по умолчанию **отключены**.

## Структура данных

```
data/
├── memory/          # ChromaDB векторная память
├── backup/          # Бекапы конфигураций
├── logs/            # Логи
├── meta_learning/   # Стратегии обучения
├── ethics/          # История этических проверок
├── jit_agents/      # Скомпилированные агенты
├── self_expansion/  # Self-Expander предложения
├── dexos/           # Контекстные дашборды
├── mesh/            # Пиры и снапшоты
├── psych/           # Когнитивная нагрузка, циркадные данные
├── evolution/       # Генетические архитектуры
├── counsel/         # Сценарии и контраргументы
├── temporal/        # Воспоминания, цели, ретроспективы
├── intent/          # Предречевые сигналы
├── prime/           # Сессии, делегирование
└── config_gui.ini   # Настройки GUI
```

## Запуск как демон

```powershell
# Через launch.bat (авто-установка зависимостей)
launch.bat --daemon

# В трей (Windows)
python main.py --dashboard
# Свернуть в трей — закрытие окна сворачивает, не завершает
```

## Обновление

```powershell
git pull
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

## Известные ограничения

1. **Ollama обязателен** для работы LLM-модулей. Без него — только rule-based режим
2. **PyAudio** может требовать установки Microsoft Visual C++ Redistributable
3. **SQLCipher** — требуется компиляция; на Windows может падать. Используется fallback на JSON
4. **Watchdog** авторестарта нет под Windows (ограничение сигналов)
5. **Gesture Control** — требует MediaPipe, камера, отключён по умолчанию
