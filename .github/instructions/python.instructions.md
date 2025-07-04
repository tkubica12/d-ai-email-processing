---
applyTo: '**/*.py'
---
- When writing APIs in Python in this project we focus on FastAPI.
- When accessing Azure services prefer AAD-based authentication and Managed Identities where possible.
- For ease of local development prefer using different default local port for each service.
- Always use docstrings for all public methods and classes explaining its purpose, parameters, return values, and exceptions.
- Never add and continuously remove any comments that document the obvious or progress of the code, only use comments to explain non-obvious lines worth extra documentation.