# Refactor code

# Refactoring stage 2
~~2. Remove all code's dependence on `config` module inside `sparq/` and make them dependent on `settings` module inside `sparq/` instead.~~

2. Separate helper functions and move appropriate functions to other places; 
    - helper functions that help sparq
    - helper functions that help other modules like config, experiments, etc.
~~3. Incorporate logic for incorporating environment variables.~~
3. ~~Incorporate logic for incorporating environment variables.~~
4. Create a cli utility to create a default config file at a specified path.
5. Create a cli utility to load environment variables from a specified .env file.
6. Implement conventional CLI behaviours such as keeping config in `~/.config/sparq/config.json` and allowing override via `--config` flag.
7. Allow developers to override settings via subclassing Settings object.
8. Create two methods `get_user_query_direct` and `get_user_query_config` and use them inside `get_user_query` method to allow for optional direct query input or config-based query input.
9. On first install,
    - create default config file at `~/.config/sparq/config.json`
    - create default .env file at `~/.config/sparq/.env`
    - create example package_config.toml at `~/.config/sparq/package_config.toml`

# Pending (from settings refactor)

- Move timestamped output dir creation out of `settings_old` — decide: `system.py` or `saver.py`
- `planner.py`: remove `settings` kwarg, use `DATA_MANIFEST_PATH` global directly
- `executor.py`: update `test_executor()` to use new settings
- `system.py`: update `_get_llms()` for pydantic model (`.model_name` instead of `['model']`), inline `load_prompts()`, derive output dirs from `AgenticSystemSettings`
- `__main__.py`: update `get_user_query` call — pass `test_query: str` directly instead of full config dict
- `helpers.py`: update `get_user_query` signature to accept `test_query: str`
- `experiments/00.py`, `experiments/hello.py`, `tests/test_get_llm.py`, `scripts/try_scripts/*.py`: replace `settings_old` imports
- Incorporate a agent recursion limit in llm settings.