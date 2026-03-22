---
name: svelte-review
description: Svelte 5 and SvelteKit code review guidelines focusing on runes, derived state, streaming patterns, and server/client state management
---

# Svelte/SvelteKit Review Guide

Focus areas: Svelte 5 runes, derived vs effects, SvelteKit streaming, server/client state separation, and component reuse.

> **TypeScript**: For TypeScript-specific patterns (type assertions, strict mode, etc.), see [ts-review](../ts-review/SKILL.md).

---

## Svelte 5 Runes

### State Management

```svelte
<script lang="ts">
  // ✅ Use $state for reactive variables
  let count = $state(0);
  let user = $state({ name: 'Alice', age: 30 });

  // ✅ State updates trigger reactivity
  function increment() {
    count++;
    user.age++; // Deep reactivity for objects
  }

  // ❌ Don't use $state for derived values
  let doubled = $state(count * 2); // Unnecessary mutable state
</script>
```

### Derived Values

```svelte
<script lang="ts">
  let items = $state([]);
  let filter = $state('');

  // ✅ $derived for computed values
  let filteredItems = $derived(
    items.filter(item => item.name.includes(filter))
  );

  // ✅ $derived.by for complex logic
  let stats = $derived.by(() => {
    const total = items.reduce((sum, item) => sum + item.price, 0);
    const avg = items.length > 0 ? total / items.length : 0;
    return { total, avg, count: items.length };
  });
</script>
```

### Props

```svelte
<script lang="ts">
  // ✅ Type-safe props with defaults
  let { 
    title, 
    count = 0, 
    onClick 
  }: { 
    title: string; 
    count?: number; 
    onClick?: () => void;
  } = $props();

  // ✅ Bindable props (parent can modify)
  let { value = $bindable('') }: { value?: string } = $props();
</script>
```

---

## Effects vs Derived vs Callbacks

### Prefer Derived Over Effects

```svelte
<script lang="ts">
  let items = $state([]);
  let search = $state('');

  // ❌ Unnecessary $effect
  $effect(() => {
    filtered = items.filter(i => i.name.includes(search));
  });

  // ✅ $derived is pure and automatic
  let filtered = $derived(items.filter(i => i.name.includes(search)));

  // ✅ Use $effect for side effects only
  $effect(() => {
    document.title = `Found ${filtered.length} items`;
  });
</script>
```

### Use Callbacks for User Actions

```svelte
<script lang="ts">
  let count = $state(0);

  // ✅ Callback for click handlers
  function handleClick() {
    count++;
  }

  // ❌ Don't use $effect for user-triggered updates
  $effect(() => {
    if (clicked) count++; // Confusing
  });
</script>

<button onclick={handleClick}>Count: {count}</button>
```

### Effect Cleanup

```svelte
<script lang="ts">
  // ✅ Cleanup subscriptions in $effect
  $effect(() => {
    const interval = setInterval(() => {
      time = Date.now();
    }, 1000);

    return () => clearInterval(interval);
  });

  // ✅ Event listeners
  $effect(() => {
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  });
</script>
```

---

## Server/Client State Separation

### No Shared State on Server

```typescript
// ❌ NEVER: Module-level variables shared across all users
let currentUser: User | null = null;

export const actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    currentUser = { name: data.get('name') }; // BUG: Shared by all users!
  }
};

// ✅ Use cookies + database for per-user state
export const actions = {
  default: async ({ request, cookies }) => {
    const session = cookies.get('session');
    const userId = await validateSession(session);
    await db.users.update(userId, { name: data.get('name') });
  }
};
```

### No Side Effects in Load

```typescript
// ❌ Never mutate global state in load
import { globalStore } from '$lib/stores';

export const load = async ({ fetch }) => {
  const user = await fetchUser();
  globalStore.set(user); // Shared across all users!
  return {};
};

// ✅ Return data from load
export const load = async ({ fetch }) => {
  const user = await fetchUser();
  return { user };
};
```

### Component State Preservation

```svelte
<script lang="ts">
  // ❌ Bug: value not recalculated on navigation
  let { data } = $props();
  const wordCount = data.content.split(' ').length;

  // ✅ Use $derived for reactive computation
  let wordCount = $derived(data.content.split(' ').length);
  let readingTime = $derived(wordCount / 250);
</script>
```

### State in URL

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  // ✅ Persist filter state in URL for SSR + shareability
  let sort = $derived(page.url.searchParams.get('sort') || 'name');
  
  function updateSort(newSort: string) {
    const url = new URL(page.url);
    url.searchParams.set('sort', newSort);
    goto(url.toString(), { keepFocus: true });
  }
</script>
```

---

## SvelteKit Streaming

### Use Streaming for Large Data Loads

```typescript
// src/routes/dashboard/+page.server.ts
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  // ✅ Return promises for streaming
  return {
    user: await getCurrentUser(),
    analytics: getAnalyticsData(), // Promise - streams
    reports: getReports(),         // Promise - streams
  };
};
```

```svelte
<script lang="ts">
  let { data } = $props();
</script>

<h1>Welcome, {data.user.name}</h1>

{#await data.analytics}
  <AnalyticsSkeleton />
{:then analyticsData}
  <AnalyticsChart data={analyticsData} />
{/await}
```

### Avoid Waterfall Requests

```typescript
// ❌ Sequential waterfall
export const load = async () => {
  const user = await fetchUser();
  const orders = await fetchOrders(user.id); // Depends on user
  const products = await fetchProducts(orders); // Depends on orders
  return { user, orders, products };
};

// ✅ Parallel independent requests
export const load = async () => {
  const [user, categories] = await Promise.all([
    fetchUser(),
    fetchCategories() // Independent of user
  ]);
  
  // Return dependent data as promise for streaming
  return {
    user,
    categories,
    orders: fetchOrders(user.id), // Streams after user loads
  };
};
```

---

## Forms

### Form Actions with Progressive Enhancement

```typescript
// src/routes/contact/+page.server.ts
import type { Actions } from './$types';
import { fail } from '@sveltejs/kit';

export const actions: Actions = {
  default: async ({ request }) => {
    const data = await request.formData();
    const email = data.get('email');
    
    if (!email || typeof email !== 'string') {
      return fail(400, { email, missing: true });
    }
    
    await sendEmail(email);
    return { success: true };
  }
};
```

```svelte
<!-- src/routes/contact/+page.svelte -->
<script lang="ts">
  import { enhance } from '$app/forms';
  
  let { form } = $props();
</script>

<form method="POST" use:enhance>
  <input name="email" type="email" />
  {#if form?.missing}
    <p class="error">Email is required</p>
  {/if}
  <button type="submit">Send</button>
</form>
```

> **Note**: Always use `use:enhance` for progressive enhancement (works without JS).

---

## Data Revalidation

### Invalidate and Refresh

```svelte
<script lang="ts">
  import { invalidate, invalidateAll } from '$app/navigation';
  
  // ✅ Refresh specific data
  async function refreshUser() {
    await invalidate('app:user');
  }
  
  // ✅ Refresh all data on page
  async function refreshAll() {
    await invalidateAll();
  }
</script>
```

---

## Component Design

### Check for Existing Components

```svelte
<script lang="ts">
  // ❌ Creating new Button component
  // Check if $lib/components/Button.svelte exists first
  
  // ✅ Import from existing component library
  import { Button, Card, Input } from '$lib/components';
</script>
```

### Don't Access page.data in Generic Components

```svelte
<!-- ❌ Generic component accessing page state -->
<script lang="ts">
  import { page } from '$app/state';
  
  // Won't be typed unless in app.d.ts
  let user = page.data.user; 
</script>

<!-- ✅ Pass data as props -->
<script lang="ts">
  let { user }: { user: User } = $props();
</script>
```

### Snippets for Composition

```svelte
<!-- Parent.svelte -->
<script lang="ts">
  import Card from './Card.svelte';
</script>

{#snippet header()}
  <h2>Card Title</h2>
{/snippet}

<Card {header}>
  <p>Default slot content</p>
</Card>
```

---

## Styling with Tailwind 4.0

```svelte
<script lang="ts">
  let { class: className = '' }: { class?: string } = $props();
</script>

<!-- ✅ Tailwind 4.0 utility classes -->
<div class="flex items-center gap-4 p-4 bg-white rounded-lg shadow-md {className}">
  <slot />
</div>

<!-- ✅ Conditional classes with class directive -->
<button 
  class="px-4 py-2 rounded"
  class:bg-blue-500={active}
  class:bg-gray-300={!active}
>
  Click
</button>
```

---

## General Guidelines

- **All .svelte files must use `<script lang="ts">`**
- **Always use `$lib/` imports** - never relative (`../`) or absolute (`/src/`) paths
- **Check `$lib/components` before creating new UI components**
- **Use Tailwind 4.0 utilities for all styling**
- **Never use module-level variables in server files** (shared across users)
- **No side effects in load functions** - return data only
- **Use $derived for reactive computations** on page navigation
- **Stream large data** - return promises from load, not awaited values
- **Parallelize independent requests** with Promise.all
- **Don't access page.data in reusable components** - pass as props
- **State in URL for filters/sorting** that should survive reload
- **Cleanup effects** always return cleanup functions
- **No stores in Svelte 5** - use runes ($state, $derived)

---

## Review Checklist

### Svelte 5 Runes
- [ ] All `<script>` tags have `lang="ts"`
- [ ] $state for mutable state (not derived)
- [ ] $derived for computed values (not $effect)
- [ ] $effect only for side effects with cleanup
- [ ] Callbacks for user interactions (not effects)
- [ ] $props with TypeScript types

### Server/Client State
- [ ] No module-level variables in server files (+page.server.ts)
- [ ] No side effects in load functions
- [ ] Use $derived for reactive page data computations
- [ ] State in URL for SSR-surviving filters
- [ ] Database + cookies for per-user state

### SvelteKit Patterns
- [ ] Stream large data with promises + {#await}
- [ ] Parallelize independent requests with Promise.all
- [ ] No waterfall data loading
- [ ] Skeleton components in {#await} blocks
- [ ] Form actions use `use:enhance`
- [ ] Form validation returns `fail()` with proper types
- [ ] `invalidate`/`invalidateAll` for data refresh

### Component Design
- [ ] Use `$lib/` imports (no relative `../` or absolute `/src/` paths)
- [ ] Check existing components in $lib/components before creating new ones
- [ ] Pass data as props to generic components (don't access page.data)
- [ ] Use Tailwind 4.0 for all styling
- [ ] Snippets for composition patterns
- [ ] No stores (use runes)

### Performance
- [ ] $derived caches automatically
- [ ] Avoid $effect for pure computations
- [ ] Stream large data, don't block
- [ ] Parallel async operations
