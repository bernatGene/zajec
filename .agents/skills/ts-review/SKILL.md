---
name: ts-review
description: TypeScript code review guidelines focusing on type safety, strict mode edge cases, async patterns, and code complexity
---

# TypeScript Code Review Guide

Focus areas: type assertions, discriminated unions, strict mode edge cases, async error handling, and code complexity.

---

## Type Safety Anti-Patterns

### Never Use `as` to Bypass Type Checking

```typescript
// ❌ as hides errors that will crash at runtime
function parseApiResponse(data: unknown): User {
  return data as User;
}

// ✅ Type guard validates structure
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    typeof (data as Record<string, unknown>).id === 'number'  // OK: as used for narrowing inside guard
  );
}
```

> **Note**: `as` is acceptable ONLY inside type guards for temporary narrowing during validation. Never use `as` to cast return types or bypass type checking.

### Non-Null Assertions Require Justification

```typescript
// ❌ ! assumes value exists without check
const user = users.find(u => u.id === id);
console.log(user!.name);

// ✅ Check before accessing
const user = users.find(u => u.id === id);
if (user) console.log(user.name);

// ✅ Or justify with comment
const validUsers = users.filter(u => u.active);
return validUsers[0]!.name; // Guaranteed: filtered above
```

### Prefer Union Types Over Enums

```typescript
// ❌ Enums add runtime overhead
enum Status { Pending = 'pending', Active = 'active' }

// ✅ Union types - compile-time only
type Status = 'pending' | 'active';

// ✅ as const for object-based constants
const HttpStatus = { OK: 200, Error: 500 } as const;
type HttpStatus = typeof HttpStatus[keyof typeof HttpStatus];
```

---

## Type Patterns

### Discriminated Unions & Exhaustiveness

```typescript
type ApiResult<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; code: number; message: string }
  | { status: 'loading' };

function handleResult<T>(result: ApiResult<T>): T | null {
  switch (result.status) {
    case 'success': return result.data;
    case 'error': console.error(result.message); return null;
    case 'loading': return null;
    default: 
      const _exhaustive: never = result; // Compile-time check
      throw new Error(`Unhandled: ${_exhaustive}`);
  }
}
```

### Generics with Constraints

```typescript
// ✅ keyof constraint
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// ✅ Sensible defaults
interface ApiResponse<T = unknown> { data: T; status: number; }
```

---

## Strict Mode

### Handle noUncheckedIndexedAccess

```typescript
// With "noUncheckedIndexedAccess": true
const user = users[0]; // Type: User | undefined

// ❌ Direct access fails
console.log(user.name); // Error: possibly undefined

// ✅ Check or default
if (user) console.log(user.name);
const u = user ?? defaultUser;
```

### Respect exactOptionalPropertyTypes

```typescript
interface Config { timeout?: number; }

// ❌ undefined !== missing
const config: Config = { timeout: undefined }; // Error

// ✅ Only set when defined
const config: Config = timeout ? { timeout } : {};
```

---

## Async Patterns

### Promise.all vs allSettled

```typescript
// ❌ all fails fast
const users = await Promise.all(ids.map(fetchUser));

// ✅ allSettled preserves all results
const results = await Promise.allSettled(ids.map(fetchUser));
const users = results
  .filter((r): r is PromiseFulfilledResult<User> => r.status === 'fulfilled')
  .map(r => r.value);
```

### Cancel Requests with AbortController

```typescript
class ApiClient {
  private controller: AbortController | null = null;

  async search(query: string) {
    this.controller?.abort();
    this.controller = new AbortController();
    return fetch(`/api/search?q=${query}`, { signal: this.controller.signal });
  }
}
```

### No Floating Promises

```typescript
// ❌ Unhandled promise
save(); // Silent failure

// ✅ Always handle
await save();
save().catch(handleError);
void save(); // Explicit ignore with comment why

// ❌ async forEach
items.forEach(async item => await process(item));

// ✅ for...of for sequential
for (const item of items) await process(item);

// ✅ Promise.all for concurrent
await Promise.all(items.map(process));
```

---

## Immutability

```typescript
// ✅ readonly prevents mutation
function process(users: readonly User[]): User[] {
  return users.filter(u => u.active);
}

// ✅ as const for literal types
const config = { api: '/api', timeout: 5000 } as const;
// Type: { readonly api: '/api'; readonly timeout: 5000 }
```

---

## Function Complexity

### Early Returns

```typescript
// ❌ Deep nesting
function processOrder(order) {
  if (order.valid) {
    if (order.items.length > 0) {
      if (order.customer.active) {
        return calculateTotal(order);
      } else {
        throw new Error('Inactive');
      }
    } else {
      throw new Error('Empty');
    }
  } else {
    throw new Error('Invalid');
  }
}

// ✅ Flatten with early returns
function processOrder(order) {
  if (!order.valid) throw new Error('Invalid');
  if (order.items.length === 0) throw new Error('Empty');
  if (!order.customer.active) throw new Error('Inactive');
  return calculateTotal(order);
}
```

### Extract Common Logic

```typescript
// ❌ Duplicated logic in branches
function calculate(item, isVip) {
  if (isVip) {
    return item.price * 0.8 + item.price * 0.8 * 0.1;
  } else {
    return item.price * 0.95 + item.price * 0.95 * 0.1;
  }
}

// ✅ Extract calculation
function calculate(item, isVip) {
  const discount = isVip ? 0.8 : 0.95;
  const base = item.price * discount;
  return base + base * 0.1;
}
```

### Helper Functions

```typescript
// ❌ Complex function mixing concerns
function processUserData(raw) {
  if (!raw.email?.includes('@')) throw new Error('Bad email');
  const name = raw.name.split(' ').map(capitalize).join(' ');
  const user = new User(raw.email, name);
  db.users.save(user);
  return user;
}

// ✅ Split into focused functions
const validateEmail = (email: string) => {
  if (!email?.includes('@')) throw new Error('Bad email');
};

const normalizeName = (name: string) => 
  name.split(' ').map(capitalize).join(' ');

function processUserData(raw) {
  validateEmail(raw.email);
  const user = new User(raw.email, normalizeName(raw.name));
  db.users.save(user);
  return user;
}
```

### Complexity Guidelines

- Functions > 50 lines or > 3 nesting levels need scrutiny
- More than 4 parameters suggests options object
- Cyclomatic complexity > 10 requires extraction
- If comment explains flow, extract to named function

---

## General Code Quality

- **Prefer `for...of` over `forEach`** - enables early returns, await, break/continue, clearer stack traces
- **Never mutate function arguments** - return new values instead
- **No magic values** - use named constants for all literals
- **No dead code** - delete unused imports, variables, commented code
- **Never throw primitives** - always throw Error instances
- **Strict equality** - use `===` and `!==` only, never `==` or `!=`
- **Boolean naming** - `isActive`, `hasPermission` not `active`, `permission`
- **No abbreviations** - except universal ones (id, url, http ok; usr, qty, len not ok)
- **Consistent error handling** - same pattern across codebase
- **Fail fast** - validate inputs at function entry, throw early
- **Single responsibility** - function does one thing
- **Minimize state** - prefer pure functions

---

## Performance

### Use Map/Set/Record for Lookups

```typescript
// ❌ O(n²) - find inside loops
for (const order of orders) {
  const user = users.find(u => u.id === order.userId); // O(n)
  process(order, user);
}

// ✅ O(n) - Map for O(1) lookup
const userById = new Map(users.map(u => [u.id, u]));
for (const order of orders) {
  const user = userById.get(order.userId);
  process(order, user);
}

// ✅ Record for string keys, Set for membership
const userByEmail: Record<string, User> = {};
for (const u of users) userByEmail[u.email] = u;

const adminIds = new Set(admins.map(a => a.id));
if (adminIds.has(userId)) { } // O(1) vs includes()
```

### Single-Pass Array Processing

```typescript
// ❌ Multiple traversals
const total = orders
  .filter(o => o.status === 'completed')
  .map(o => o.amount)
  .reduce((a, b) => a + b, 0);
const count = orders.filter(o => o.status === 'completed').length;

// ✅ Single traversal with for...of
let total = 0, count = 0;
for (const order of orders) {
  if (order.status === 'completed') {
    total += order.amount;
    count++;
  }
}

// Or use reduce if preferred
const stats = orders.reduce((acc, o) => {
  if (o.status === 'completed') { acc.total += o.amount; acc.count++; }
  return acc;
}, { total: 0, count: 0 });
```

### Other Patterns

- **Array spread** - `[...arr, item]` is O(n); use push for large arrays
- **JSON operations** - avoid parse/stringify in tight loops
- **Memoization** - cache expensive computations sparingly
- **Lazy loading** - defer heavy imports until needed
- **Event listeners** - always clean up to prevent leaks
- **Bundle imports** - import specific functions, not entire libraries

---

## Review Checklist

### Type Safety
- [ ] No `as` assertions (use type guards)
- [ ] No `any` (use `unknown` + validation)
- [ ] `!` non-null assertions justified with comment
- [ ] Discriminated unions with exhaustiveness checks
- [ ] Union types preferred over enums

### Strict Mode
- [ ] Handle `| undefined` from indexed access
- [ ] `exactOptionalPropertyTypes` respected
- [ ] No `@ts-ignore` (use `@ts-expect-error` with reason)

### Async
- [ ] Promise.all vs allSettled chosen correctly
- [ ] AbortController for cancellable requests
- [ ] No floating promises
- [ ] for...of vs Promise.all chosen correctly

### Immutability
- [ ] `readonly` for array/object parameters
- [ ] `as const` for literal objects

### Complexity
- [ ] Early returns reduce nesting
- [ ] Common logic extracted outside branches
- [ ] Helper functions for complex operations
- [ ] Functions < 50 lines, < 3 nesting levels

### General Quality
- [ ] Prefer `for...of` over `forEach`
- [ ] No magic values (use named constants)
- [ ] No dead code (unused imports, commented code)
- [ ] Error instances not primitives
- [ ] Boolean variables properly named (`isX`, `hasY`)

### Performance
- [ ] Map/Set/Record for O(1) lookups instead of find/filter in loops
- [ ] Single-pass array processing vs multiple traversals
- [ ] Event listeners properly cleaned up
