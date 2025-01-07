check:
    ruff format chalsedony/*.py
    ruff check chalsedony --fix
    pyright chalsedony
    ruff format chalsedony/*.py
    mypy --strict chalsedony
    # vulture chalsedony/*.py

run:
    python chalsedony/main.py --no-dark-mode


embed-assets:
    pyside6-rcc chalsedony/static/static.qrc                       -o static_resources_rc.py
    pyside6-rcc chalsedony/static/katex/dist/katex.qrc             -o katex_resources_rc.py
    # Katex looks under /fonts first, then looks relative
    # Without this Qresource pollutes the STDOUT with warnings
    # Just make a copy of them I guess
    pyside6-rcc chalsedony/static/katex/dist/fonts/katex_fonts.qrc -o katex_fonts_rc.py

