---
name: wp-post
description: Read or write posts and pages on bhanunuthakki.com directly via the WordPress REST API — list posts, inspect a post's content, create or update a draft, fix a typo, add a category or tag. Use when the user says "update my blog post", "fix this on the blog", "what's on my blog", "create a draft", "add a category", "change the artifacts page", or names a specific post to edit.
---

# Direct WordPress post work

For one-off post and page work that isn't a source-doc sync. Read `AGENTS.md`
before writing anything. Before drafting or revising public copy, read
`../plain-writing/SKILL.md`.

## Setup facts

- Site: `https://www.bhanunuthakki.com`, REST base `/wp-json/wp/v2`
- Credentials: `C:\Users\bhanu\.gemini\.secrets\wordpress.env` (site URL,
  username, application password). Loaded by
  `blog_engine.credentials.load_wordpress_credentials`.
- Auth is HTTP Basic with the application password. It goes in the
  `Authorization` header — **never** in a URL or query string, and never into a
  log line or exception message.
- **The site uses Gutenberg block markup**, not classic HTML. A post body is
  `<!-- wp:paragraph --><p>…</p><!-- /wp:paragraph -->` and so on. Posting raw
  HTML produces a post that looks fine on the front end but is uneditable in the
  block editor. Always go through `blog_engine.markdown_blocks.markdown_to_blocks`
  — write Markdown, convert at the boundary.

Current taxonomy: categories `career`, `climate`, `market maps`,
`mental models`, `recommendations` (plus `books` and `investing`, created on
first use by the sync pipeline). Tags: `career`, `climate`, `Investing`.

## Procedure

Prefer the Python client over raw `curl` — it is typed, it resolves category
slugs to IDs, and it refuses unsafe writes:

```python
from blog_engine.config import load_settings
from blog_engine.credentials import load_wordpress_credentials
from blog_engine.wordpress import WordPressClient
```

**Reading** is unrestricted. To inspect a post's actual block markup you need
`?context=edit` and authentication — `content.rendered` won't show block comments.

**Writing** — the rules, in order of importance:

1. **Never publish.** Create and update with `status=draft`. Publishing is a
   human action in WP Admin.
2. **Never modify a published post without explicit approval in this
   conversation.** `update_post` refuses when the target isn't a draft. If he asks
   you to fix a typo in a live post, that's approval for that specific edit —
   confirm which post and what change, then do it. It is not approval for
   anything else on that post or any other.
3. **Read before you write.** Fetch the current content and show him what you're
   changing. An update replaces the whole body; a partial payload silently
   destroys the rest.
4. **Pages are riskier than posts.** `home`, `artifacts`, `investing`,
   `questions`, `influences`, `contact` are all live and hand-built. Read the
   existing block markup and match its structure rather than regenerating the page
   from scratch.

## Report

For a write: what changed, the edit link, and the status (which should be
`draft`). For a read: answer the question — don't dump the raw block markup unless
he asked for it.

## Never

- Publish, or flip a draft to `publish`.
- Post raw HTML instead of blocks.
- Put the app password anywhere except the `Authorization` header.
- Delete a post or page. If he wants something gone, move it to draft and tell him
  it's reversible from there.
