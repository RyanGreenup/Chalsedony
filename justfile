check:
    ruff format chalsedony/**/*.py
    ruff check chalsedony --fix
    pyright chalsedony
    ruff format chalsedony/**/*.py
    mypy --strict chalsedony | grep -v rc | grep -v missing-import | grep -v 'missing library stubs' | grep -v 'ignore'
    # vulture chalsedony/*.py
    check-mypy

check-mypy:
    mypy --strict chalsedony | grep -v rc | grep -v missing-import | grep -v 'missing library stubs' | grep -v 'ignore'

run:
    uv run -- python chalsedony/main.py


embed-assets:
    # todo finish sas
    npx sass chalsedony/static/styles/markdown.scss chalsedony/static/css/markdown.css
    npx sass chalsedony/static/styles/admonitions.scss chalsedony/static/css/admonitions.css

    # QRC
    pyside6-rcc chalsedony/static/static.qrc                       -o chalsedony/static_resources_rc.py
    pyside6-rcc chalsedony/static/katex/dist/katex.qrc             -o chalsedony/katex_resources_rc.py
    # Katex looks under /fonts first, then looks relative
    # Without this Qresource pollutes the STDOUT with warnings
    # Just make a copy of them I guess
    pyside6-rcc chalsedony/static/katex/dist/fonts/katex_fonts.qrc -o chalsedony/katex_fonts_rc.py

