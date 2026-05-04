# 🧠 The Learning Journey: Building a Live Translation Engine

This file serves as a mentor's log to explain the architecture, concepts, and "why" behind our code.

---

## 🎓 Lesson 8: Reading the SDK Map
### 1. The "Keyword" Problem
Every library has its own specific names for parameters. Even if "API Key" is common, one library might call it `api_key`, another `token`, and another `api_subscription_key`.
### 2. Tracebacks are your friends
The error `unexpected keyword argument 'api_key'` told us exactly what was wrong: we used a name the computer didn't recognize.
### 3. Debugging as Research
When an SDK fails, the first step is always to check the "Constructor" (the `__init__` method) in the documentation to find the exact names it wants.

---

## 🎓 Lesson 7: The "Diagnostic" Mindset
### 1. When all else fails: Print it!
If your code says a file "doesn't exist" but you see it with your own eyes, you have a **Perspective Conflict**. You and Python are looking at the world differently.
### 2. Path Awareness
On Windows, paths can be absolute (`D:\...`) or relative (`./...`). Diagnostic prints like `os.getcwd()` (Get Current Working Directory) help you see the world through Python's eyes.
### 3. "Visibility" is Debugging
By printing the first few characters of a key (NEVER the whole key!), you can verify it's loaded without compromising security.

---

## 🎓 Lesson 6: Explicit Loading (The "Brute Force" Method)
... (Previous lessons preserved)
