check:
    ruff format draftsmith/*.py
    ruff check draftsmith --fix
    pyright draftsmith
    ruff format draftsmith/*.py
    mypy --strict draftsmith
    # vulture draftsmith/*.py

run:
    python draftsmith/main.py --no-dark-mode
