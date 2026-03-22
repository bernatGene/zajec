---
name: python-review
description: Python code review guidelines focusing on non-obvious patterns, advanced typing, async patterns, and testing organization
---

# Python Code Review Guide

Focus areas: advanced type patterns, async/await edge cases, testing organization, and performance-critical decisions.

---

## Type Annotations

### Use Modern Type Syntax (Python 3.12)

```python
# ❌ Old style - NEVER use in Python 3.12
from typing import Optional, Union, List, Dict, Set, Tuple
from __future__ import annotations  # NEVER import this

def find_user(user_id: int) -> Optional[User]:
    pass

def get_names(users: List[User]) -> Dict[str, int]:
    pass

# ✅ Modern syntax - always use this
def find_user(user_id: int) -> User | None:
    pass

def get_names(users: list[User]) -> dict[str, int]:
    pass

def process(items: set[int]) -> tuple[str, int]:
    pass
```

### Pathlib Over os.path

```python
from pathlib import Path

# ❌ Old os.path style
import os
file_path = os.path.join(os.path.dirname(__file__), 'data', 'file.txt')

# ✅ Modern pathlib
file_path = Path(__file__).parent / 'data' / 'file.txt'

# ✅ Pathlib methods
if file_path.exists():
    content = file_path.read_text()
```

### TypedDict and Pydantic for API Contracts

Use TypedDict for simple structures, Pydantic for validation (especially in FastAPI):

```python
from typing import TypedDict, Required, NotRequired

# ✅ TypedDict for simple structures
class UserDict(TypedDict):
    id: int
    name: str
    email: str
    age: NotRequired[int]  # Python 3.11+

# ✅ Pydantic for validation (preferred in FastAPI apps)
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    age: int | None = None

def create_user(data: UserDict | UserCreate) -> User:
    return User(**data)
```

### Generics and TypeVar

```python
from typing import TypeVar, Generic, Callable

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# ✅ Generic functions
def first(items: list[T]) -> T | None:
    return items[0] if items else None

# ✅ Constrained TypeVar
from typing import Hashable
H = TypeVar('H', bound=Hashable)

def dedupe(items: list[H]) -> list[H]:
    return list(set(items))

# ✅ Generic classes
class Cache(Generic[K, V]):
    def __init__(self) -> None:
        self._data: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self._data.get(key)

    def set(self, key: K, value: V) -> None:
        self._data[key] = value
```

---

## Async Patterns

### Task Management

```python
import asyncio

# ✅ Use TaskGroup (Python 3.11+)
async def fetch_multiple():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(fetch_url("url1"))
        task2 = tg.create_task(fetch_url("url2"))
    # Auto-waits all, exceptions propagate
    return task1.result(), task2.result()

# ✅ Proper cancellation handling
async def good_worker():
    try:
        while True:
            await do_work()
    except asyncio.CancelledError:
        await cleanup()
        raise  # Re-raise so caller knows
```

### Mixing Sync and Async

```python
from concurrent.futures import ThreadPoolExecutor

# ✅ Run blocking code in executor
async def run_sync_in_async():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        blocking_io_function,
        arg1, arg2
    )

# ✅ Never use time.sleep in async
def run_async_in_sync():
    return asyncio.run(async_function())
```

### Rate Limiting and Concurrency Control

```python
# ✅ Semaphore for limiting concurrent work
async def fetch_with_limit(urls: list[str], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str) -> str:
        async with semaphore:
            return await fetch_url(url)

    return await asyncio.gather(*[fetch_one(url) for url in urls])

# ✅ Queue for producer-consumer
async def producer_consumer():
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

    async def producer():
        for item in items:
            await queue.put(item)
        await queue.put(None)  # Sentinel

    async def consumer():
        while True:
            item = await queue.get()
            if item is None:
                break
            await process(item)
            queue.task_done()

    await asyncio.gather(producer(), consumer())
```

---

## Error Handling

### Exception Chaining

```python
# ❌ Loses original traceback
try:
    result = external_api.call()
except APIError as e:
    raise RuntimeError("API failed")  # Lost the cause

# ✅ Preserves chain
try:
    result = external_api.call()
except APIError as e:
    raise RuntimeError("API failed") from e
```

### Custom Exception Hierarchies

```python
# ✅ Define business exceptions
class AppError(Exception):
    """Base application exception"""
    pass

class ValidationError(AppError):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str | int):
        self.resource = resource
        self.id = id
        super().__init__(f"{resource} with id {id} not found")
```

### Context Managers and Exceptions

```python
from contextlib import contextmanager

# ✅ Handle rollback properly
@contextmanager
def transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ✅ ExceptionGroup for batch operations (Python 3.11+)
def process_batch(items: list) -> None:
    errors = []
    for item in items:
        try:
            process(item)
        except Exception as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Batch processing failed", errors)
```

---

## Performance

### Data Structure Choices

```python
from collections import Counter, defaultdict, deque

# ✅ Use right data structure
word_counts = Counter(words)  # vs manual dict counting
most_common = word_counts.most_common(10)

# Default dict eliminates key checks
graph = defaultdict(list)
graph[node].append(neighbor)  # No "if node not in graph"

# Deque for O(1) at both ends
queue = deque()
queue.appendleft(item)  # O(1) vs list O(n)
```

### Generators for Large Data

```python
# ✅ Generator for lazy loading
def get_all_users():
    for row in db.fetch_all():
        yield User(row)

# ✅ Generator expression for sums
sum_of_squares = sum(x**2 for x in range(1000000))

# ✅ itertools for iteration patterns
from itertools import islice, chain, groupby

first_10 = list(islice(infinite_generator(), 10))
all_items = chain(list1, list2, list3)

for key, group in groupby(sorted(items, key=get_key), key=get_key):
    process_group(key, list(group))
```

### Caching Strategies

```python
from functools import lru_cache, cache

# ✅ LRU cache for expensive calls
@lru_cache(maxsize=128)
def expensive_computation(n: int) -> int:
    return sum(i**2 for i in range(n))

# ✅ @cache for unlimited (Python 3.9+)
@cache
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# ✅ Manual cache when you need TTL
class DataService:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._cache_ttl: dict[str, float] = {}

    def get_data(self, key: str) -> Any:
        if key in self._cache and time.time() < self._cache_ttl[key]:
            return self._cache[key]
        data = self._fetch_data(key)
        self._cache[key] = data
        self._cache_ttl[key] = time.time() + 300
        return data
```

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# ✅ Thread pool for IO-bound
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_url, urls))

# ✅ Process pool for CPU-bound
with ProcessPoolExecutor() as executor:
    results = list(executor.map(heavy_computation, data))

# ✅ as_completed for early results
with ThreadPoolExecutor() as executor:
    futures = {executor.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):
        url = futures[future]
        try:
            result = future.result()
        except Exception as e:
            print(f"{url} failed: {e}")
```

### Prefer NumPy Over Loops

```python
import numpy as np

# ❌ Python loops over numeric data
result = []
for i in range(len(data)):
    result.append(data[i] * 2 + offset)

# ✅ NumPy vectorized operations (10-100x faster)
result = np.array(data) * 2 + offset

# ❌ Manual aggregation
sum_squared = 0
for x in data:
    sum_squared += x ** 2
mean = sum_squared / len(data)

# ✅ NumPy aggregation
mean = np.mean(np.array(data) ** 2)
```

---

## Control Flow Complexity

### Short-Circuit with Early Returns

```python
# ❌ Deep nesting with else
def process_order(order):
    if order.valid:
        if order.items:
            if order.customer.active:
                return calculate_total(order)
            else:
                raise ValueError("Inactive customer")
        else:
            raise ValueError("No items")
    else:
        raise ValueError("Invalid order")

# ✅ Early returns reduce nesting
def process_order(order):
    if not order.valid:
        raise ValueError("Invalid order")
    if not order.items:
        raise ValueError("No items")
    if not order.customer.active:
        raise ValueError("Inactive customer")
    return calculate_total(order)
```

### Extract Common Logic

```python
# ❌ Duplicated logic in branches
def calculate_price(item, is_vip):
    if is_vip:
        base = item.base_price
        discount = base * 0.2
        tax = (base - discount) * 0.1
        return base - discount + tax
    else:
        base = item.base_price
        discount = base * 0.05
        tax = (base - discount) * 0.1
        return base - discount + tax

# ✅ Extract common logic
def calculate_price(item, is_vip):
    base = item.base_price
    discount_rate = 0.2 if is_vip else 0.05
    discount = base * discount_rate
    tax = (base - discount) * 0.1
    return base - discount + tax
```

### Use Helper Functions

```python
# ❌ Complex function doing too much
def process_user_data(raw_data):
    # Validation
    if not raw_data.get("email"):
        raise ValueError("Missing email")
    if "@" not in raw_data["email"]:
        raise ValueError("Invalid email")
    
    # Transformation
    name_parts = raw_data["name"].split()
    normalized_name = " ".join(part.capitalize() for part in name_parts)
    
    # Persistence
    user = User(email=raw_data["email"], name=normalized_name)
    db.session.add(user)
    db.session.commit()
    return user

# ✅ Split into focused helpers
def validate_user_data(data: dict) -> None:
    if not data.get("email"):
        raise ValueError("Missing email")
    if "@" not in data["email"]:
        raise ValueError("Invalid email")

def normalize_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())

def save_user(email: str, name: str) -> User:
    user = User(email=email, name=name)
    db.session.add(user)
    db.session.commit()
    return user

def process_user_data(raw_data: dict) -> User:
    validate_user_data(raw_data)
    normalized_name = normalize_name(raw_data["name"])
    return save_user(raw_data["email"], normalized_name)
```

### Question Complex Functions

- Functions longer than 50 lines warrant scrutiny
- More than 3 levels of nesting is a red flag
- Cyclomatic complexity > 10 suggests extraction needed
- If you need a comment to explain the flow, extract it

---

## Testing

### Organization & Patterns

```python
from unittest.mock import Mock, patch, AsyncMock, ANY
from typing import Generator

# ✅ Classes for related tests
class TestUserAuthentication:
    def test_login_with_valid_credentials(self, user):
        assert authenticate(user.email, "password") is True

# ✅ Parameterized tests
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("", ""),
])
def test_uppercase(input: str, expected: str):
    assert input.upper() == expected

# ✅ Mock and verify
@patch("myapp.services.external_api.call")
def test_with_patched_api(mock_call):
    mock_call.return_value = {"status": "ok"}
    result = process_data()
    assert result["status"] == "ok"

# ✅ Fixtures with cleanup
@pytest.fixture
def database() -> Generator[Database, None, None]:
    db = Database()
    db.connect()
    yield db
    db.disconnect()

# ✅ Marks for filtering
@pytest.mark.slow
def test_large_data_processing():
    pass
# Run: pytest -m "not slow"
```

---

## Review Checklist

### Type Safety
- [ ] Use `|` syntax for unions (not `Optional`/`Union`)
- [ ] NEVER use `from __future__ import annotations`
- [ ] NEVER import `List`, `Dict`, `Set`, `Tuple` from typing
- [ ] Use TypedDict or Pydantic for API contracts
- [ ] Use TypeVar for generic constraints
- [ ] `pathlib` instead of `os.path`

### Async Code
- [ ] Use TaskGroup (3.11+) or proper gather patterns
- [ ] Handle CancelledError with cleanup
- [ ] Use run_in_executor for blocking calls
- [ ] Semaphore for rate limiting

### Error Handling
- [ ] Use `from` to preserve exception chains
- [ ] Custom exception hierarchies for business logic
- [ ] Proper rollback in context managers
- [ ] ExceptionGroup for batch operations

### Performance
- [ ] collections module (Counter, defaultdict, deque)
- [ ] Generators for large datasets
- [ ] Caching strategy appropriate (lru_cache vs manual TTL)
- [ ] Right executor type (Thread vs Process)
- [ ] NumPy for numeric operations instead of loops

### Control Flow
- [ ] Early returns to reduce nesting
- [ ] Common logic extracted outside conditionals
- [ ] Helper functions for complex operations
- [ ] Functions under 50 lines and < 3 nesting levels

### Testing
- [ ] Classes to organize related tests
- [ ] Parameterized tests for multiple scenarios
- [ ] Marks for slow/integration tests
- [ ] AsyncMock for async patches
- [ ] Fixtures with proper cleanup
