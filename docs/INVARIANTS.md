# Инварианты безопасности Dex

## Формальные утверждения, гарантируемые архитектурой

### 1. Файловая песочница

```
∀ path ∈ Filesystem:
    Sandbox.validate_read(path) ⇒ normalized(path) ∈ whitelist
    Sandbox.validate_write(path) ⇒ normalized(path) ∈ whitelist
    Sandbox.is_dangerous(path) ⇒ path ∉ whitelist
```

**Гарантия:** Агент не может прочитать или записать файл за пределами белого списка, независимо от переданного пути (абсолютный/относительный/символическая ссылка).

### 2. Kill Switch

```
trigger() ∈ {True, False}
trigger() = True ⇒ ∀ agent ∈ Agents: agent.shutdown()
trigger() = True ⇒ stop_processing()
trigger() = True ⇒ log("KILL_SWITCH_ACTIVATED")

∀ command ∈ Commands:
    contains(command, "стоп код") ⇒ trigger()
```

**Гарантия:** Kill switch останавливает всех агентов и прекращает обработку. Не может быть проигнорирован.

### 3. Конституция

```
∀ command ∈ Commands:
    ConstitutionalChecker.check(command) = VIOLATION ⇒
        block_execution(command) ∧ log(violation, article_id)

ConstitutionalChecker.rules = immutableset(8 статей)
self_improvement_loop.edit(ConstitutionalChecker) = ⊥
```

**Гарантия:** 8 статей конституции неизменяемы петлёй самоулучшения. Нарушение = блокировка команды.

### 4. Приватный режим

```
privacy_mode = ON ⇒
    microphone.active = False ∧
    camera.active = False ∧
    gesture.active = False ∧
    log("PRIVACY_MODE_ENTERED")
```

**Гарантия:** Все сенсоры отключаются в приватном режиме.

### 5. Этический сопроцессор

```
∀ action ∈ Actions:
    EthicalCoProcessor.evaluate(action).consensus = FORBIDDEN ⇒
        block_execution(action) ∧ log(veto_reason)
```

**Гарантия:** Консенсус этических фреймворков имеет право вето.

### 6. Hot Swap

```
∀ component ∈ Components:
    HotSwapper.swap(component, new_version) ⇒
        traffic_split = (A:B) ∧
        rollback_possible(previous_version) ∧
        A/B_test_confidence ≥ 0.95 ⇒ full_deploy
```

**Гарантия:** Замена компонента всегда имеет A/B-тест и возможность отката.

### 7. Фабрика команд

```
∀ handler ∈ CommandHandlers:
    handler.prefix ∈ keys(handler_map)
    handler.prefix = longest_match(command) ⇒ handler(command)
```

**Гарантия:** Выполняется самый специфичный хендлер (по длине префикса).

### 8. Self-Expander

```
∀ patch ∈ SelfExpander.generated_patches:
    patch.is_applied ⇒
        has_git_commit(patch.hash) ∧
        previous_state.backup_exists ∧
        rollback_possible(previous_state)
```

**Гарантия:** Любое изменение кода через SelfExpander версионируется в Git и имеет бекап.

## Проверка при сборке

```powershell
# Запуск всех тестов инвариантов
set DEX_SKIP_LLM=1
pytest tests/ -v --tb=short
```

Для property-based тестов (дополнительно):
```powershell
pip install hypothesis
pytest tests/ -v -k "property"
```
