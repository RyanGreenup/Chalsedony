# Chalsedony - A Modern Note-Taking Application

Chalsedony is an open-source note-taking application built with Python and Qt, designed for compatability with [Joplin](https://github.com/laurent22/joplin) it aims to bring a performant keyboard centric UI.

![](./assets/screenshot.png)

## Key Features

✨ **Modern Qt Interface**
Enjoy a sleek, responsive user interface with dark/light mode support, zoom and Neovim Integration.

📚 **SQLite Backend**
Notes are stored in a reliable SQLite database with full compatability with Joplin, this gives us free Full Text Search and no broken links.

🔗 **Note Linking**
Create connections between notes with a keyboard shortcut for inserting links (No Plugins needed!)

📅 **Journal Integration**
Built-in Keyboard shortcut to focus on today's journal entry (`YYYY-MM-DD`)

🔍 *Search**
Uses the Same FTS as Joplin (FTS4 right now `#TODO upgrade to FTS5`)

📝 **Markdown pymdown extensions**
Write and preview notes using Markdown with some extra features like admonitions.

⚙️ **Hackable**
Edit the source!

## Getting Started

### Prerequisites

* `uv`

### Installation

```bash
uv tool install git+https://github.com/ryangreenup/chalsedony
cy
```

### Uninstallation

```bash
uv tool uninstall chalsedony
```

## Contributing

PR's Welcome!

## License

Chalsedony is released under the GPL License.

## Why Chalsedony?

I figure Chalsedony is a gemstone like Obsidian, but it's a bit more clear and versatile.

## TODO Documentation

There are some additional features like datatables



    /// tab | Previw
    /// note | Admonitions
    This is a note
    ///
    ///
    ///tab | Source
    ```markdown
    /// note | Admonitions
    This is a note
    ///
    ```
    ///
    ///tab | HTML
    ```html
    <div class="admonition" markdown="1">
    <p class="admonition-title" markdown="1"> Some title</p>
    <p>Some content</p>
    </div>
    ```
    ///


    ```mermaid
    graph TD
        A[Hard] -->|Text| B(Round)
        B --> C{Decision}
        C -->|One| D[Result 1]
        C -->|Two| E[Result 2]
    ```



    [=85% "85%"]{: .candystripe}
    [=100% "100%"]{: .candystripe .candystripe-animate}
    [=0%]{: .thin}
    [=5%]{: .thin}
    [=25%]{: .thin}
    [=45%]{: .thin}
    [=65%]{: .thin}
    [=85%]{: .thin}
    [=100%]{: .thin}


    Aligned images:

    ![](:/{id}){width="100px" align=right}

    Captions:

    ![](:/{id})
    /// caption
        attrs: {class: "thumbnail tiny"}
    A Caption
    ///



    Datatables


    /// tab | Output
    /// html | div.dataTablesContainer[style='border: 1px solid red;']

    | Name                | Position                  | Office        | Age | Start date | Salary    |
    |---------------------|---------------------------|---------------|-----|------------|-----------|
    | Tiger Nixon         | System Architect          | Edinburgh     | 61  | 2011-04-25 | \$320,800 |
    | Garrett Winters     | Accountant                | Tokyo         | 63  | 2011-07-25 | \$170,750 |
    | Ashton Cox          | Junior Technical Author   | San Francisco | 66  | 2009-01-12 | \$86,000  |

    ///



    <div
        class="dataTablesContainer"
        markdown="1">
    </div>
