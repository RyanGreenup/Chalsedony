check:
    ruff format chalsedony/*.py
    ruff check chalsedony --fix
    pyright chalsedony
    ruff format chalsedony/*.py
    mypy --strict chalsedony
    # vulture chalsedony/*.py

run:
    python chalsedony/main.py --no-dark-mode
