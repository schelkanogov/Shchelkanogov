# Архитектура интеграции локальной LLM (GigaChat) в VulnDetector

## 1. Концептуальная схема (Mermaid)

```mermaid
graph TD
    subgraph "Infrastructure (Local/Private Cloud)"
        SberLLM["<b>GigaChat On-Premise</b><br/>(Local LLM)"]
        RAG["<b>RAG Database</b><br/>(Vector DB: Leads & Vulns)"]
        Scanners["<b>Security Scanners</b><br/>(Nuclei, Nmap, Snyk)"]
    end

    subgraph "Orchestration Layer"
        KB["<b>KanbanBridge</b><br/>(Orchestrator Logic)"]
        AP["<b>AutoPatch Module</b><br/>(Self-Healing)"]
    end

    subgraph "Interfaces & Delivery"
        TG["Telegram Bot / Admin"]
        EMAIL["Email Reports (IT Immunity)"]
        CICD["CI/CD Pipeline Gate"]
    end

    %% Data Flow
    Scanners -- "Raw Scan JSON" --> KB
    KB -- "Context Retrieval" --> RAG
    RAG -- "Historical Data" --> KB
    
    KB -- "Prompt + Context" --> SberLLM
    SberLLM -- "Reasoning & Fix Code" --> KB
    
    KB -- "Task Creation" --> TG
    KB -- "Vulnerability Report" --> EMAIL
    KB -- "Decision (Pass/Fail)" --> CICD
    
    KB -- "Execution Command" --> AP
    AP -- "Patch Applied" --> CICD
```

## 2. Детальное описание компонентов

### 🔐 Sber GigaChat On-Premise (Local LLM)
Ядро системы. Используется для:
-   **Анализа сырых логов**: Преобразование тысяч строк вывода сканеров в понятную бизнес-логику.
-   **Генерации патчей**: Написание SQL-инъекционных фильтров, конфигураций Nginx или обновлений Dockerfile.
-   **Классификации**: Автоматическое определение приоритета (Critical, High, Medium) на основе корпоративных стандартов.

### 🧠 RAG (Retrieval-Augmented Generation)
Система использует 2,000+ исторических отчетов (лидов), собранных за 2 года:
-   **Векторный поиск**: Когда находится новая уязвимость, RAG ищет, встречалась ли она раньше и как была решена.
-   **Persistence**: Все новые сканы дообучают систему в режиме реального времени.

### ⚙️ KanbanBridge (Orchestrator)
"Мозг", написанный на Python, который:
-   Слушает Telegram и Почту.
-   Управляет очередями задач в Kanboard.
-   Оркестрирует вызовы GigaChat API (через внутренний прокси).

### 🛠 AutoPatch Module
Модуль "IT-Иммунитета", который получает от LLM готовый код исправления и применяет его в тестовой среде (Staging) перед подтверждением администратором.

## 3. Почему это важно для Sber500?
1.  **Конфиденциальность**: Данные не покидают периметр компании (GigaChat On-Prem).
2.  **Масштабируемость**: Один ИИ-агент заменяет команду из 3-5 AppSec инженеров.
3.  **Скорость**: Время от обнаружения до патча сокращается с дней до минут.
